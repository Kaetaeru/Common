from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

API_BASE = "https://api.apluscoursereview.com/api"
SITE_URL = "https://apluscoursereview.com/"
SUBJECTS_URL = f"{API_BASE}/subject?pageSize=0"
COURSES_URL = f"{API_BASE}/course?pageSize=0"
_REQUEST_TIMEOUT = 4.0
_SUCCESS_TTL = 15 * 60.0
_FAILURE_TTL = 5 * 60.0

_cache_lock = threading.Lock()
_cache_expires_at = 0.0
_cache_snapshot: dict[str, Any] | None = None


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "APU-Schedule-Builder/1.2",
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


def instructor_signature(value: Any) -> tuple[str, ...]:
    text = str(value or "").strip()
    text = re.sub(r"^Course section taught by\s+", "", text, flags=re.IGNORECASE)
    text = text.rstrip(". ")
    tokens = re.findall(r"[^\W_]+", text.upper(), flags=re.UNICODE)
    return tuple(sorted(tokens))


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


def build_review_index(subject_payload: Any, course_payload: Any) -> dict[tuple[str, tuple[str, ...]], dict[str, Any]]:
    subjects_by_id: dict[Any, str] = {}
    for subject in _data(subject_payload):
        code = normalize_subject_code(subject.get("subjectCode"))
        subject_id = subject.get("id")
        if code and subject_id is not None:
            subjects_by_id[subject_id] = code

    grouped: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for course in _data(course_payload):
        subject_id = course.get("subjectId")
        subject_code = subjects_by_id.get(subject_id)
        signature = instructor_signature(course.get("description"))
        if not subject_code or not signature:
            continue
        key = (subject_code, signature)
        bucket = grouped.setdefault(
            key,
            {
                "subjectId": subject_id,
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
            "courseId": bucket["courseIds"][0] if bucket["courseIds"] else None,
            "rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "reviewCount": len(reviews),
            "recommendPercent": round(sum(recommended) * 100 / len(recommended)) if recommended else None,
            "sourceUrl": SITE_URL,
        }
    return result


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


def _fetch_snapshot() -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        subject_future = pool.submit(_fetch_subjects)
        course_future = pool.submit(_fetch_json, COURSES_URL)
        subjects = subject_future.result()
        courses = course_future.result()
    index = build_review_index(subjects, courses)
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
        signature = instructor_signature(section.get("instructor"))
        review = index.get((subject_code, signature)) if subject_code and signature else None
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
