from __future__ import annotations

import json
import os
import re
import tempfile
import time
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
    payload = json.dumps(dict(sorted(mapping.items())), ensure_ascii=False, indent=2) + "\n"
    last_error: OSError | None = None

    for attempt in range(6):
        temp_name = None
        try:
            fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            os.replace(temp_name, path)
            return
        except OSError as exc:
            last_error = exc
            if temp_name:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
            retryable = isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {5, 32, 33}
            if not retryable or attempt == 5:
                raise
            time.sleep(0.05 * (2 ** attempt))

    if last_error is not None:
        raise last_error
