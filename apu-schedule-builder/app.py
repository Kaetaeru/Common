from __future__ import annotations

import json
import os
import ssl
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import app_backend as _backend
from aplus_reviews import enrich_schedule_data
from language_rules import annotate_schedule_data, filter_candidate_subjects
from syllabus_mapping import load_verified_mapping, mapping_fingerprint, parse_direct_syllabus_url
from app_backend import *  # noqa: F401,F403 - preserve the public API used by tests and scripts


_original_download_file = _backend.download_file
_original_load_or_build_data = _backend.load_or_build_data
_original_do_GET = _backend.Handler.do_GET
_original_solve_variant = _backend.solve_variant
_STATIC_FILES = {
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app-core.js": ("app-core.js", "application/javascript; charset=utf-8"),
    "/app-ui.js": ("app-ui.js", "application/javascript; charset=utf-8"),
    "/app-events.js": ("app-events.js", "application/javascript; charset=utf-8"),
    "/app-profile.js": ("app-profile.js", "application/javascript; charset=utf-8"),
    "/aplus.css": ("aplus.css", "text/css; charset=utf-8"),
}


def _running_on_windows() -> bool:
    return os.name == "nt"


def _is_certificate_verification_error(exc: BaseException) -> bool:
    pending: list[BaseException] = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, ssl.SSLCertVerificationError):
            return True
        text = str(current).lower()
        if "certificate_verify_failed" in text or "certificate verify failed" in text:
            return True
        for attr in ("reason", "__cause__", "__context__"):
            nested = getattr(current, attr, None)
            if isinstance(nested, BaseException):
                pending.append(nested)
    return False


def _download_with_windows_trust(url: str, destination: Path) -> None:
    """Download through Windows PowerShell/SChannel without disabling TLS checks."""
    env = os.environ.copy()
    env["APU_SB_DOWNLOAD_URL"] = url
    env["APU_SB_DOWNLOAD_OUT"] = str(destination)
    command = (
        "$ErrorActionPreference='Stop';"
        "$ProgressPreference='SilentlyContinue';"
        "Invoke-WebRequest -Uri $env:APU_SB_DOWNLOAD_URL "
        "-OutFile $env:APU_SB_DOWNLOAD_OUT -UseBasicParsing"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            env=env,
        )
        data = destination.read_bytes()
        if len(data) < 1000:
            raise ValueError("Downloaded file was unexpectedly small.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _download_file_with_windows_cert_fallback(url: str, destination: Path) -> None:
    try:
        _original_download_file(url, destination)
    except Exception as exc:
        if not _running_on_windows() or not _is_certificate_verification_error(exc):
            raise
        try:
            _download_with_windows_trust(url, destination)
        except Exception as fallback_exc:
            raise RuntimeError(
                "APU HTTPS download failed certificate verification in Python and also failed "
                "with the Windows trusted certificate store. Check Windows date/time, VPN/proxy, "
                "security software, and Windows root-certificate updates."
            ) from fallback_exc


# app_backend resolves this global at call time, so its normal data-loading flow now
# gets the verified Windows trust-store fallback without duplicating the backend.
_backend.download_file = _download_file_with_windows_cert_fallback
download_file = _download_file_with_windows_cert_fallback


def _load_syllabus_link_overrides_from_repository() -> dict[str, str]:
    return load_verified_mapping(_backend.DATA_DIR)


# The schedule app and the separate collector use the same verified mapping reader.
_backend.load_syllabus_link_overrides = _load_syllabus_link_overrides_from_repository
load_syllabus_link_overrides = _load_syllabus_link_overrides_from_repository


def _apply_verified_syllabus_links(sections, academic_year) -> None:
    overrides = _load_syllabus_link_overrides_from_repository()
    for section in sections:
        class_code = _backend.code_text(section.get("classCode"))
        direct = _backend.clean_text(section.get("syllabusUrl"))
        if direct and _backend.is_direct_syllabus_url(direct, class_code, academic_year):
            continue
        section.pop("syllabusUrl", None)
        if academic_year is None:
            continue
        override = overrides.get(f"{academic_year}:{class_code}", "")
        parsed = parse_direct_syllabus_url(override)
        # The repository reader already validated the key. For verified grouped
        # aliases, only the URL year must equal the active academic year.
        if parsed and parsed[0] == int(academic_year):
            section["syllabusUrl"] = override


_backend.apply_syllabus_links = _apply_verified_syllabus_links
apply_syllabus_links = _apply_verified_syllabus_links


def _load_or_build_data_with_mapping_cache(college: str, allow_download: bool = True) -> dict:
    college = college.upper()
    fingerprint = mapping_fingerprint(_backend.DATA_DIR)
    cached = _backend.normalized_path(college)
    timetable_path, subject_path = _backend.source_paths(college)
    cache_verified = True

    if cached.exists():
        try:
            cached_data = json.loads(cached.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached_data = {}
        previous = cached_data.get("syllabusMappingFingerprint")
        if previous != fingerprint:
            if timetable_path.exists() and subject_path.exists():
                cached.unlink(missing_ok=True)
            else:
                cache_verified = False

    data = _original_load_or_build_data(college, allow_download=allow_download)
    if cache_verified:
        data["syllabusMappingFingerprint"] = fingerprint
        data["syllabusMappingCacheVerified"] = True
        cached.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        data["syllabusMappingCacheVerified"] = False

    # A+ is optional live enrichment. It is applied after the APU cache write so
    # ratings never become stale data inside the normalized timetable cache.
    return enrich_schedule_data(annotate_schedule_data(data))


_backend.load_or_build_data = _load_or_build_data_with_mapping_cache
load_or_build_data = _load_or_build_data_with_mapping_cache


def _solve_variant_with_language_profile(data, config, variant, beam_size=220):
    return _original_solve_variant(filter_candidate_subjects(data, config), config, variant, beam_size)


_backend.solve_variant = _solve_variant_with_language_profile
solve_variant = _solve_variant_with_language_profile


def _do_GET_with_static_assets(self) -> None:
    parsed = urlparse(self.path)
    static = _STATIC_FILES.get(parsed.path)
    if static:
        filename, content_type = static
        self.send_file(_backend.WEB_DIR / filename, content_type)
        return
    _original_do_GET(self)


_backend.Handler.do_GET = _do_GET_with_static_assets
Handler = _backend.Handler


if __name__ == "__main__":
    _backend.main()
