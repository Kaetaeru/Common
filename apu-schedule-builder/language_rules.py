from __future__ import annotations

import re
import unicodedata
from typing import Any

JAPANESE = "JA"
ENGLISH = "EN"

LANGUAGE_LEVEL_LABELS = {
    JAPANESE: [
        "Foundation Japanese I",
        "Foundation Japanese II",
        "Foundation Japanese III",
        "Intermediate Japanese",
        "Pre-Advanced Japanese",
        "Advanced Japanese",
    ],
    ENGLISH: [
        "Elementary English",
        "Pre-Intermediate English",
        "Intermediate English",
        "Upper-Intermediate English",
        "Advanced English 1",
        "Advanced English 2",
    ],
}


def _normalized_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def classify_language_course(name: Any) -> tuple[str, int, str] | None:
    """Return (language, ordered core level, label) for the required level ladder only."""
    text = _normalized_name(name)

    japanese_patterns = [
        (3, r"^foundation japanese iii(?:\b|$)"),
        (2, r"^foundation japanese ii(?:\b|$)"),
        (1, r"^foundation japanese i(?:\b|$)"),
        (5, r"^pre[- ]advanced japanese(?:\b|$)"),
        (4, r"^intermediate japanese(?:\b|$)"),
        (6, r"^advanced japanese(?:\b|$)"),
    ]
    for rank, pattern in japanese_patterns:
        if re.search(pattern, text):
            return JAPANESE, rank, LANGUAGE_LEVEL_LABELS[JAPANESE][rank - 1]

    english_patterns = [
        (2, r"^pre[- ]intermediate english(?:\s+[ab])?(?:\b|$)"),
        (4, r"^upper[- ]intermediate english(?:\s+[ab])?(?:\b|$)"),
        (1, r"^elementary english(?:\s+[ab])?(?:\b|$)"),
        (3, r"^intermediate english(?:\s+[ab])?(?:\b|$)"),
        (5, r"^advanced english 1\s*[ab]?(?:\b|$)"),
        (6, r"^advanced english 2\s*[ab]?(?:\b|$)"),
    ]
    for rank, pattern in english_patterns:
        if re.search(pattern, text):
            return ENGLISH, rank, LANGUAGE_LEVEL_LABELS[ENGLISH][rank - 1]

    return None


def annotate_schedule_data(data: dict[str, Any]) -> dict[str, Any]:
    """Attach transient language-ladder metadata without changing the normalized cache schema."""
    subject_meta: dict[str, tuple[str, int, str]] = {}
    for subject in data.get("subjects", []):
        meta = classify_language_course(subject.get("name"))
        if not meta:
            continue
        language, rank, label = meta
        subject["languageCore"] = language
        subject["languageLevelRank"] = rank
        subject["languageLevelLabel"] = label
        subject_meta[str(subject.get("subjectCode") or "")] = meta
        for section in subject.get("sections", []):
            section["languageCore"] = language
            section["languageLevelRank"] = rank
            section["languageLevelLabel"] = label

    for section in data.get("sections", []):
        meta = subject_meta.get(str(section.get("subjectCode") or "")) or classify_language_course(section.get("name"))
        if not meta:
            continue
        language, rank, label = meta
        section["languageCore"] = language
        section["languageLevelRank"] = rank
        section["languageLevelLabel"] = label
    return data


def language_eligibility_reason(subject: dict[str, Any], config: dict[str, Any]) -> str:
    core = str(subject.get("languageCore") or "").upper()
    rank = int(subject.get("languageLevelRank") or 0)
    if not core or not rank:
        return ""

    track = str(config.get("track") or "E").upper()
    completed = max(0, int(config.get("languageLevel") or 0))

    if track == "E" and core == ENGLISH:
        return "English Basis · core English level course"
    if track in {"JST", "JAT"} and core == JAPANESE:
        return "Japanese Basis · core Japanese level course"

    if track == "JAT" and core == ENGLISH:
        completed = max(completed, 4)

    opposite = (track == "E" and core == JAPANESE) or (track in {"JST", "JAT"} and core == ENGLISH)
    if opposite and completed and rank <= completed:
        label = str(subject.get("languageLevelLabel") or subject.get("name") or "language course")
        return f"{label} · at or below completed language level"
    return ""


def filter_candidate_subjects(data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Filter only solver candidates; top-level sections stay intact so fixed university classes still work."""
    filtered = dict(data)
    filtered["subjects"] = [
        subject for subject in data.get("subjects", [])
        if not language_eligibility_reason(subject, config)
    ]
    return filtered
