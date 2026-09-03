from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

KEY_RE = re.compile(r"^(20\d{2}):(\d{4,6})$")
TAIL_RE = re.compile(r"^(20\d{2})(\d{4,6})$")


def parse_direct_url(url: Any) -> tuple[int, str] | None:
    text = str(url or "").strip()
    if not text:
        return None
    try:
        parsed = urlparse(text)
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.netloc.lower() != "syllabus.apu.ac.jp":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 5 or parts[:3] != ["syllabus", "s", "a-syllabus"] or not parts[3]:
        return None
    match = TAIL_RE.fullmatch(parts[4])
    return (int(match.group(1)), match.group(2)) if match else None


def valid_direct_url(url: Any, year: int, class_code: str) -> bool:
    return parse_direct_url(url) == (int(year), str(class_code))


def load_mapping(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        match = KEY_RE.fullmatch(str(key))
        url = str(value or "").strip()
        if match and valid_direct_url(url, int(match.group(1)), match.group(2)):
            result[str(key)] = url
    return result


def save_mapping(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dict(sorted(mapping.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
