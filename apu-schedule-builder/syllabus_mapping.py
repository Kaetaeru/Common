from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_KEY_RE = re.compile(r"^(20\d{2}):(\d{4,6})$")
_TAIL_RE = re.compile(r"^(20\d{2})(\d{4,6})$")


def parse_direct_syllabus_url(url: Any) -> tuple[int, str] | None:
    text = str(url or "").strip()
    if not text:
        return None
    try:
        parsed = urlparse(text)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "syllabus.apu.ac.jp":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 5 or parts[:3] != ["syllabus", "s", "a-syllabus"] or not parts[3]:
        return None
    match = _TAIL_RE.fullmatch(parts[4])
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def validate_mapping_entry(key: Any, url: Any) -> tuple[str | None, str | None]:
    key_text = str(key or "").strip()
    url_text = str(url or "").strip()
    match = _KEY_RE.fullmatch(key_text)
    if not match:
        return None, "key must be YYYY:ClassCode"
    parsed = parse_direct_syllabus_url(url_text)
    if not parsed:
        return None, "URL is not an APU direct syllabus URL"
    year, class_code = parsed
    if year != int(match.group(1)) or class_code != match.group(2):
        return None, "key and URL year/Class code do not match"
    return key_text, None


def mapping_source_files(data_dir: Path) -> list[Path]:
    files: list[Path] = []
    legacy = data_dir / "syllabus_links.json"
    if legacy.is_file():
        files.append(legacy)
    batch_root = data_dir / "syllabus-links"
    if batch_root.is_dir():
        files.extend(sorted(path for path in batch_root.rglob("*.json") if path.is_file()))
    return files


def scan_mapping_sources(data_dir: Path) -> dict[str, Any]:
    data_dir = Path(data_dir)
    files = mapping_source_files(data_dir)
    seen_urls: dict[str, set[str]] = {}
    key_sources: dict[str, list[str]] = {}
    problems: list[dict[str, str]] = []
    source_reports: list[dict[str, Any]] = []
    duplicate_count = 0

    for path in files:
        relative = path.relative_to(data_dir).as_posix()
        source = {"path": relative, "entries": 0, "valid": 0, "invalid": 0}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append({"source": relative, "key": "", "reason": f"JSON read failed: {exc}"})
            source["error"] = str(exc)
            source_reports.append(source)
            continue
        if not isinstance(raw, dict):
            problems.append({"source": relative, "key": "", "reason": "top-level JSON must be an object"})
            source["error"] = "top-level JSON must be an object"
            source_reports.append(source)
            continue

        source["entries"] = len(raw)
        for key, url in raw.items():
            normalized_key, error = validate_mapping_entry(key, url)
            if error:
                source["invalid"] += 1
                problems.append({"source": relative, "key": str(key), "reason": error})
                continue
            assert normalized_key is not None
            source["valid"] += 1
            url_text = str(url).strip()
            urls = seen_urls.setdefault(normalized_key, set())
            if url_text in urls:
                duplicate_count += 1
            urls.add(url_text)
            key_sources.setdefault(normalized_key, []).append(relative)
        source_reports.append(source)

    mapping: dict[str, str] = {}
    conflicts: list[dict[str, Any]] = []
    for key, urls in sorted(seen_urls.items()):
        if len(urls) == 1:
            mapping[key] = next(iter(urls))
        else:
            conflicts.append({
                "key": key,
                "urls": sorted(urls),
                "sources": key_sources.get(key, []),
            })

    return {
        "mapping": mapping,
        "sources": source_reports,
        "keySources": key_sources,
        "problems": problems,
        "conflicts": conflicts,
        "duplicateCount": duplicate_count,
    }


def load_verified_mapping(data_dir: Path) -> dict[str, str]:
    return scan_mapping_sources(data_dir)["mapping"]


def mapping_fingerprint(data_dir: Path) -> str:
    mapping = load_verified_mapping(data_dir)
    canonical = json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
