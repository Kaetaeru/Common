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
    parsed = parse_direct_url(url)
    if parsed == (int(year), str(class_code)):
        return True

    # SearchURL instances from strict_search carry grouped-result evidence only
    # for the current process. Require the target and canonical Class codes to
    # both be present in the same APU result anchor before accepting a mismatch.
    group_codes = tuple(str(code) for code in getattr(url, "group_codes", ()) or ())
    return bool(
        parsed
        and parsed[0] == int(year)
        and len(group_codes) >= 2
        and str(class_code) in group_codes
        and parsed[1] in group_codes
    )


def load_mapping(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}

    candidates: dict[str, tuple[str, tuple[int, str]]] = {}
    exact: dict[str, str] = {}
    for key, value in raw.items():
        key_text = str(key)
        match = KEY_RE.fullmatch(key_text)
        url = str(value or "").strip()
        parsed = parse_direct_url(url)
        if not match or not parsed or parsed[0] != int(match.group(1)):
            continue
        candidates[key_text] = (url, parsed)
        if parsed[1] == match.group(2):
            exact[key_text] = url

    result: dict[str, str] = dict(exact)
    for key, (url, parsed) in candidates.items():
        if key in result:
            continue
        canonical_key = f"{parsed[0]}:{parsed[1]}"
        if exact.get(canonical_key) == url:
            result[key] = url
    return result


def save_mapping(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    # Persist the canonical key beside a verified grouped alias. That gives the
    # JSON enough structure for load_mapping() to distinguish an intentional
    # grouped syllabus from an arbitrary mismatched key/URL pair after restart.
    normalized = dict(mapping)
    for key, value in list(mapping.items()):
        match = KEY_RE.fullmatch(str(key))
        parsed = parse_direct_url(value)
        group_codes = tuple(str(code) for code in getattr(value, "group_codes", ()) or ())
        if not match or not parsed or len(group_codes) < 2:
            continue
        target = match.group(2)
        if parsed[0] != int(match.group(1)) or target not in group_codes or parsed[1] not in group_codes:
            continue
        normalized.setdefault(f"{parsed[0]}:{parsed[1]}", str(value))
        normalized[str(key)] = str(value)

    payload = json.dumps(dict(sorted(normalized.items())), ensure_ascii=False, indent=2) + "\n"
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
