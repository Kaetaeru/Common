from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable

API_BASE = "https://api.apluscoursereview.com/api"
SITE_URL = "https://apluscoursereview.com/"
SUBJECTS_URL = f"{API_BASE}/subject?pageSize=0"
COURSES_URL = f"{API_BASE}/course?pageSize=0"
INSTRUCTORS_URL = f"{API_BASE}/instructor"
_REQUEST_TIMEOUT = 4.0
_SUCCESS_TTL = 15 * 60.0
_FAILURE_TTL = 5 * 60.0

_cache_lock = threading.Lock()
_cache_expires_at = 0.0
_cache_snapshot: dict[str, Any] | None = None

_GENERIC_INSTRUCTOR_TEXT = {
    "instructor to be announced",
    "instructor tba",
    "tba",
    "tbd",
}


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "APU-Schedule-Builder/1.3",
        },
    )
    with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _data(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return [item for item in payload["data"] if isinstance(item, dict)]
    return []


def normalize_subject_code(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _clean_instructor_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^Course section taught by\s+", "", text, flags=re.IGNORECASE)
    text = text.rstrip(". ")
    return text.strip()


def instructor_signature(value: Any) -> tuple[str, ...]:
    text = _clean_instructor_text(value)
    if not text or text.casefold() in _GENERIC_INSTRUCTOR_TEXT:
        return ()
    tokens = re.findall(r"[^\W_]+", text.upper(), flags=re.UNICODE)
    return tuple(sorted(tokens))


def relaxed_instructor_signature(signature: Iterable[str]) -> tuple[str, ...]:
    tokens = tuple(signature)
    without_initials = tuple(token for token in tokens if len(token) > 1)
    # Keep initials when removing them would leave only one meaningful token.
    return without_initials if len(without_initials) >= 2 else tokens


def _instructor_name_from_api(item: dict[str, Any]) -> str:
    for key in ("fullName", "name", "instructorName", "displayName"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    first = str(item.get("firstName") or item.get("givenName") or "").strip()
    last = str(item.get("lastName") or item.get("familyName") or item.get("surname") or "").strip()
    return " ".join(part for part in (first, last) if part)


def _instructor_signatures_by_id(course_payload: Any, instructor_payload: Any = None) -> dict[Any, set[tuple[str, ...]]]:
    signatures: dict[Any, set[tuple[str, ...]]] = defaultdict(set)

    # A+ course descriptions are useful for older records, but many reviewed
    # records have description=null. Reuse a known name from another course
    # with the same stable instructorId before giving up on that reviewed row.
    for course in _data(course_payload):
        instructor_id = course.get("instructorId")
        signature = instructor_signature(course.get("description"))
        if instructor_id is not None and signature:
            signatures[instructor_id].add(signature)

    # The public site also exposes an instructor endpoint. Treat it as an
    # optional enrichment source so A+ downtime/schema drift never breaks the
    # schedule builder. The flexible field extraction keeps this fail-soft.
    for instructor in _data(instructor_payload):
        instructor_id = instructor.get("id")
        name = _instructor_name_from_api(instructor)
        signature = instructor_signature(name)
        if instructor_id is not None and signature:
            signatures[instructor_id].add(signature)

    return signatures


def _best_known_signature(signatures: Iterable[tuple[str, ...]]) -> tuple[str, ...]:
    candidates = sorted(set(signatures), key=lambda item: (len(item), item))
    if not candidates:
        return ()
    if len(candidates) == 1:
        return candidates[0]
    # Some A+ rows reuse one instructorId while the description lists a
    # co-teacher as well. Prefer the unique smallest signature only when its
    # tokens are contained in every longer candidate; otherwise stay
    # conservative and leave the course unmatched.
    smallest = candidates[0]
    smallest_tokens = set(smallest)
    if all(smallest_tokens.issubset(set(candidate)) for candidate in candidates[1:]):
        return smallest
    return ()


def _course_signatures(course: dict[str, Any], by_id: dict[Any, set[tuple[str, ...]]]) -> set[tuple[str, ...]]:
    direct = instructor_signature(course.get("description"))
    if direct:
        return {direct}
    instructor_id = course.get("instructorId")
    recovered = _best_known_signature(by_id.get(instructor_id, set()))
    return {recovered} if recovered else set()


def _review_key(review: dict[str, Any]) -> tuple[Any, ...]:
    review_id = review.get("id")
    if review_id is not None:
        return ("id", review_id)
    return (
        "fallback",
        review.get("rating"),
        review.get("isRecommended"),
        review.get("createdAt"),
        review.get("overallExperience"),
    )


def build_review_index(
    subject_payload: Any,
    course_payload: Any,
    instructor_payload: Any = None,
) -> dict[tuple[str, tuple[str, ...]], dict[str, Any]]:
    subjects_by_id: dict[Any, str] = {}
    for subject in _data(subject_payload):
        code = normalize_subject_code(subject.get("subjectCode"))
        subject_id = subject.get("id")
        if code and subject_id is not None:
            subjects_by_id[subject_id] = code

    signatures_by_id = _instructor_signatures_by_id(course_payload, instructor_payload)
    grouped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for course in _data(course_payload):
        subject_id = course.get("subjectId")
        subject_code = subjects_by_id.get(subject_id)
        signatures = _course_signatures(course, signatures_by_id)
        if not subject_code or not signatures:
            continue
        for signature in signatures:
            key = (subject_code, signature)
            bucket = grouped.setdefault(
                key,
                {
                    "subjectId": subject_id,
                    "instructorId": course.get("instructorId"),
                    "courseIds": [],
                    "reviews": {},
                },
            )
            course_id = course.get("id")
            if course_id is not None and course_id not in bucket["courseIds"]:
                bucket["courseIds"].append(course_id)
            for review in course.get("reviews") or []:
                if isinstance(review, dict):
                    bucket["reviews"][_review_key(review)] = review

    result: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for key, bucket in grouped.items():
        reviews = list(bucket["reviews"].values())
        ratings = [float(r["rating"]) for r in reviews if isinstance(r.get("rating"), (int, float))]
        recommended = [bool(r.get("isRecommended")) for r in reviews if isinstance(r.get("isRecommended"), bool)]
        result[key] = {
            "subjectId": bucket["subjectId"],
            "instructorId": bucket["instructorId"],
            "courseId": bucket["courseIds"][0] if bucket["courseIds"] else None,
            "rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "reviewCount": len(reviews),
            "recommendPercent": round(sum(recommended) * 100 / len(recommended)) if recommended else None,
            "sourceUrl": f"{SITE_URL}subject/{bucket['subjectId']}",
        }
    return result


def find_review(
    index: dict[tuple[str, tuple[str, ...]], dict[str, Any]],
    subject_code: str,
    instructor: Any,
) -> dict[str, Any] | None:
    signature = instructor_signature(instructor)
    if not subject_code or not signature:
        return None
    exact = index.get((subject_code, signature))
    if exact is not None:
        return exact

    relaxed = relaxed_instructor_signature(signature)
    section_tokens = set(relaxed)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    for (code, candidate_signature), review in index.items():
        if code != subject_code:
            continue
        candidate_relaxed = relaxed_instructor_signature(candidate_signature)
        candidate_tokens = set(candidate_relaxed)
        if len(candidate_tokens) < 2:
            continue
        # Handles omitted middle initials/names and a timetable cell that lists
        # more than one instructor. Only accept the fallback when it resolves
        # to one unique A+ instructor/course; ambiguous co-teaching stays blank.
        if candidate_relaxed == relaxed or candidate_tokens.issubset(section_tokens):
            marker = (review.get("instructorId"), review.get("courseId"))
            if marker not in seen:
                seen.add(marker)
                candidates.append(review)
    return candidates[0] if len(candidates) == 1 else None


def _fetch_subjects() -> Any:
    try:
        return _fetch_json(SUBJECTS_URL)
    except Exception:
        payload = _fetch_json(f"{API_BASE}/subject")
        pagination = payload.get("pagination") if isinstance(payload, dict) else None
        total = pagination.get("totalCount") if isinstance(pagination, dict) else None
        items = _data(payload)
        if isinstance(total, int) and total > len(items):
            return _fetch_json(f"{API_BASE}/subject?pageSize={total}")
        return payload


def _fetch_instructors_optional() -> Any:
    try:
        return _fetch_json(INSTRUCTORS_URL)
    except Exception:
        return []


def _fetch_snapshot() -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=3) as pool:
        subject_future = pool.submit(_fetch_subjects)
        course_future = pool.submit(_fetch_json, COURSES_URL)
        instructor_future = pool.submit(_fetch_instructors_optional)
        subjects = subject_future.result()
        courses = course_future.result()
        instructors = instructor_future.result()
    index = build_review_index(subjects, courses, instructors)
    return {
        "available": True,
        "index": index,
        "subjectCount": len({key[0] for key in index}),
        "courseCount": len(index),
    }


def get_review_snapshot(*, refresh: bool = False) -> dict[str, Any]:
    global _cache_expires_at, _cache_snapshot
    now = time.monotonic()
    with _cache_lock:
        if not refresh and _cache_snapshot is not None and now < _cache_expires_at:
            return _cache_snapshot

    try:
        snapshot = _fetch_snapshot()
        ttl = _SUCCESS_TTL
    except Exception:
        snapshot = {"available": False, "index": {}, "subjectCount": 0, "courseCount": 0}
        ttl = _FAILURE_TTL

    with _cache_lock:
        _cache_snapshot = snapshot
        _cache_expires_at = now + ttl
    return snapshot


def _apply_to_sections(
    sections: list[dict[str, Any]],
    index: dict[tuple[str, tuple[str, ...]], dict[str, Any]],
) -> set[str]:
    matched: set[str] = set()
    for section in sections:
        section.pop("aplusReview", None)
        subject_code = normalize_subject_code(section.get("subjectCode") or section.get("subjectCd"))
        review = find_review(index, subject_code, section.get("instructor"))
        if review is not None:
            section["aplusReview"] = dict(review)
            class_code = str(section.get("classCode") or "")
            if class_code:
                matched.add(class_code)
    return matched


def enrich_schedule_data(data: dict[str, Any]) -> dict[str, Any]:
    snapshot = get_review_snapshot()
    index = snapshot["index"] if snapshot.get("available") else {}
    matched = _apply_to_sections(data.get("sections", []), index)
    for subject in data.get("subjects", []):
        matched |= _apply_to_sections(subject.get("sections", []), index)
    data["aplusReviewStatus"] = {
        "available": bool(snapshot.get("available")),
        "matchedSections": len(matched),
        "source": SITE_URL,
    }
    return data
