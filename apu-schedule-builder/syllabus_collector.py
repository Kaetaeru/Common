from __future__ import annotations

import json
import re
import socket
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import app as schedule_app
from syllabus_mapping import load_verified_mapping, parse_direct_syllabus_url, scan_mapping_sources, validate_mapping_entry

ROOT = Path(__file__).resolve().parent
COLLECTOR_DIR = ROOT / "collector"
DATA_DIR = schedule_app.DATA_DIR
_BATCH_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _event(level: str, message: str) -> dict[str, str]:
    return {"level": level, "message": message}


def _dataset(college: str, allow_download: bool = False) -> dict[str, Any]:
    return schedule_app.load_or_build_data(college.upper(), allow_download=allow_download)


def _term_slug(data: dict[str, Any]) -> str:
    year = data.get("academicYear")
    season = str(data.get("academicSeason") or "unknown").lower()
    return f"{year}-{season}" if year else "unknown-term"


def collector_status(college: str, allow_download: bool = False) -> dict[str, Any]:
    college = college.upper()
    events: list[dict[str, str]] = []
    try:
        data = _dataset(college, allow_download=allow_download)
    except Exception as exc:
        return {
            "ok": False,
            "college": college,
            "error": str(exc),
            "events": [_event("error", f"{college} dataset load failed: {exc}")],
        }

    year = int(data.get("academicYear") or 0)
    sections = data.get("sections", [])
    by_code = {str(section.get("classCode", "")): section for section in sections}
    scan = scan_mapping_sources(DATA_DIR)
    mapping = scan["mapping"]
    relevant = {
        key: url for key, url in mapping.items()
        if key.startswith(f"{year}:") and key.split(":", 1)[1] in by_code
    }
    unknown = [
        key for key in mapping
        if key.startswith(f"{year}:") and key.split(":", 1)[1] not in by_code
    ]

    mismatches = []
    attached = 0
    class_rows = []
    for code, section in sorted(by_code.items(), key=lambda item: (str(item[1].get("name", "")).lower(), item[0])):
        key = f"{year}:{code}"
        expected = relevant.get(key)
        actual = str(section.get("syllabusUrl") or "").strip()
        mapped = expected is not None
        if mapped and actual == expected:
            attached += 1
        elif mapped:
            mismatches.append({"classCode": code, "expected": expected, "actual": actual})
        class_rows.append({
            "classCode": code,
            "name": section.get("name", ""),
            "instructor": section.get("instructor", ""),
            "term": section.get("term", ""),
            "mapped": mapped,
            "syllabusUrl": expected or actual,
            "source": ", ".join(scan["keySources"].get(key, [])),
        })

    for source in scan["sources"]:
        if source.get("error"):
            events.append(_event("error", f"{source['path']}: {source['error']}"))
        else:
            events.append(_event(
                "info",
                f"Read {source['path']}: {source['valid']} valid / {source['invalid']} invalid",
            ))
    for problem in scan["problems"][:100]:
        events.append(_event("error", f"{problem['source']} {problem['key']}: {problem['reason']}"))
    for conflict in scan["conflicts"][:100]:
        events.append(_event("error", f"Conflicting URLs for {conflict['key']} ({len(conflict['urls'])} variants)"))
    if unknown:
        events.append(_event("warn", f"{len(unknown)} verified mapping key(s) do not exist in the loaded {college} dataset"))

    cache_verified = bool(data.get("syllabusMappingCacheVerified", True))
    reader_verified = cache_verified and not mismatches and attached == len(relevant)
    if not cache_verified:
        events.append(_event("error", "Normalized cache could not be rebuilt from source XLSX; repository mapping attachment is not fully trustworthy"))
    if relevant:
        level = "ok" if reader_verified else "error"
        events.append(_event(level, f"App reader attachment check: {attached}/{len(relevant)} repository mappings attached"))
    else:
        events.append(_event("warn", "No repository mapping exists for this dataset yet; attachment check has nothing to verify"))

    mapped_codes = {key.split(":", 1)[1] for key in relevant}
    return {
        "ok": True,
        "college": college,
        "term": data.get("term"),
        "academicYear": year,
        "termSlug": _term_slug(data),
        "stats": {
            "classes": len(class_rows),
            "mapped": len(mapped_codes),
            "unmapped": len(class_rows) - len(mapped_codes),
            "invalid": len(scan["problems"]),
            "conflicts": len(scan["conflicts"]),
            "sources": len(scan["sources"]),
            "attached": attached,
        },
        "readerVerified": reader_verified,
        "cacheVerified": cache_verified,
        "readerExpected": len(relevant),
        "readerAttached": attached,
        "mismatches": mismatches,
        "unknownMappings": unknown,
        "classes": class_rows,
        "sources": scan["sources"],
        "problems": scan["problems"],
        "conflicts": scan["conflicts"],
        "events": events,
    }


def _parse_input_pairs(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    text = (text or "").strip()
    if not text:
        return [], ["input is empty"]
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raw = None
    if isinstance(raw, dict):
        return [(str(key).strip(), str(url).strip()) for key, url in raw.items()], []

    pairs: list[tuple[str, str]] = []
    errors: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        url_match = re.search(r"https?://\S+", line)
        if not url_match:
            errors.append(f"line {line_number}: no URL found")
            continue
        url = url_match.group(0).rstrip(",;)]}\"")
        parsed = parse_direct_syllabus_url(url)
        if not parsed:
            errors.append(f"line {line_number}: not an APU direct syllabus URL")
            continue
        year, class_code = parsed
        prefix = line[:url_match.start()].strip().rstrip(":,|-\t ")
        if prefix:
            token = prefix.split()[-1]
            if ":" in token and token != f"{year}:{class_code}":
                errors.append(f"line {line_number}: key does not match URL")
                continue
            if token.isdigit() and token != class_code:
                errors.append(f"line {line_number}: Class code does not match URL")
                continue
        pairs.append((f"{year}:{class_code}", url))
    return pairs, errors


def validate_import(text: str, college: str) -> dict[str, Any]:
    status = collector_status(college, allow_download=False)
    if not status.get("ok"):
        return status
    year = status["academicYear"]
    known_codes = {row["classCode"] for row in status["classes"]}
    existing = load_verified_mapping(DATA_DIR)
    pairs, parse_errors = _parse_input_pairs(text)
    accepted: dict[str, str] = {}
    rejected: list[dict[str, str]] = []
    duplicates: list[str] = []
    events = [_event("error", error) for error in parse_errors]

    for key, url in pairs:
        normalized_key, error = validate_mapping_entry(key, url)
        if error:
            rejected.append({"key": key, "url": url, "reason": error})
            events.append(_event("error", f"{key}: {error}"))
            continue
        assert normalized_key is not None
        entry_year, class_code = normalized_key.split(":", 1)
        if int(entry_year) != year:
            reason = f"URL is AY{entry_year}, loaded dataset is AY{year}"
            rejected.append({"key": normalized_key, "url": url, "reason": reason})
            events.append(_event("error", f"{normalized_key}: {reason}"))
            continue
        if class_code not in known_codes:
            reason = f"Class {class_code} is not in the loaded {college.upper()} dataset"
            rejected.append({"key": normalized_key, "url": url, "reason": reason})
            events.append(_event("error", f"{normalized_key}: {reason}"))
            continue
        old = existing.get(normalized_key)
        if old:
            if old == url:
                duplicates.append(normalized_key)
                events.append(_event("warn", f"{normalized_key}: already mapped to the same URL"))
            else:
                reason = "repository already has a different verified URL"
                rejected.append({"key": normalized_key, "url": url, "reason": reason})
                events.append(_event("error", f"{normalized_key}: {reason}"))
            continue
        if normalized_key in accepted and accepted[normalized_key] != url:
            reason = "input contains two different URLs for the same key"
            rejected.append({"key": normalized_key, "url": url, "reason": reason})
            events.append(_event("error", f"{normalized_key}: {reason}"))
            accepted.pop(normalized_key, None)
            continue
        accepted[normalized_key] = url
        events.append(_event("ok", f"{normalized_key}: verified"))

    return {
        "ok": True,
        "accepted": dict(sorted(accepted.items())),
        "rejected": rejected,
        "duplicates": duplicates,
        "events": events,
        "json": json.dumps(dict(sorted(accepted.items())), ensure_ascii=False, indent=2) + "\n",
        "termSlug": status["termSlug"],
    }


def save_batch(college: str, batch_name: str, entries: dict[str, str]) -> dict[str, Any]:
    batch_name = (batch_name or "").strip()
    if not _BATCH_RE.fullmatch(batch_name):
        raise ValueError("Batch name may contain only letters, numbers, dot, underscore, and hyphen.")
    if not batch_name.endswith(".json"):
        batch_name += ".json"
    validation = validate_import(json.dumps(entries), college)
    accepted = validation.get("accepted", {})
    if not accepted:
        raise ValueError("No new verified entries to save.")
    status = collector_status(college, allow_download=False)
    folder = DATA_DIR / "syllabus-links" / status["termSlug"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / batch_name

    current: dict[str, str] = {}
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Existing {path.name} is not a JSON object.")
        current = {str(key): str(value) for key, value in raw.items()}
    for key, url in accepted.items():
        if key in current and current[key] != url:
            raise ValueError(f"{key} already exists in {path.name} with a different URL.")
        current[key] = url
    path.write_text(json.dumps(dict(sorted(current.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    relative = path.relative_to(ROOT).as_posix()
    return {
        "ok": True,
        "path": relative,
        "saved": len(accepted),
        "events": validation["events"] + [_event("ok", f"Saved {len(accepted)} verified link(s) to {relative}")],
        "status": collector_status(college, allow_download=False),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "APUSyllabusCollector/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        print("[collector]", format % args)

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 5_000_000:
            raise ValueError("Request body too large.")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_file(COLLECTOR_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/collector.css":
            self.send_file(COLLECTOR_DIR / "collector.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/collector.js":
            self.send_file(COLLECTOR_DIR / "collector.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/api/status":
            college = parse_qs(parsed.query).get("college", ["APM"])[0]
            self.send_json(collector_status(college, allow_download=False))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            college = str(payload.get("college", "APM")).upper()
            if parsed.path == "/api/load":
                self.send_json(collector_status(college, allow_download=True))
                return
            if parsed.path == "/api/validate":
                self.send_json(validate_import(str(payload.get("text", "")), college))
                return
            if parsed.path == "/api/save-batch":
                entries = payload.get("entries", {})
                if not isinstance(entries, dict):
                    raise ValueError("entries must be a JSON object")
                self.send_json(save_batch(college, str(payload.get("batchName", "batch-001")), entries))
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc), "events": [_event("error", str(exc))]}, 400)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    try:
        port = 8766
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        port = find_free_port()
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"APU Syllabus Collector running at {url}")
    print("Press Ctrl+C to stop.")
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
