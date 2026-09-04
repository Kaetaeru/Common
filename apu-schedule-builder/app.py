from __future__ import annotations

import json
import os
import ssl
import subprocess
from pathlib import Path

import app_backend as _backend
from aplus_reviews import enrich_schedule_data
from language_rules import annotate_schedule_data, filter_candidate_subjects
from syllabus_mapping import mapping_fingerprint
from app_backend import *  # noqa: F401,F403 - preserve the public API used by tests and scripts


_original_download_file = _backend.download_file
_original_load_or_build_data = _backend.load_or_build_data
_original_solve_variant = _backend.solve_variant


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


def _load_or_build_data_with_mapping_cache(college: str, allow_download: bool = True) -> dict:
    college = college.upper()
    fingerprint = mapping_fingerprint(_backend.DATA_DIR)
    cached = _backend.normalized_path(college)
    timetable_path, subject_path = _backend.source_paths(college)
    cache_verified = True
    needs_write = True

    if cached.exists():
        try:
            cached_data = json.loads(cached.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached_data = {}
        previous = cached_data.get("syllabusMappingFingerprint")
        # A cache that already carries this fingerprint and schema needs no
        # rewrite, so a plain read stays a read.
        needs_write = (
            previous != fingerprint
            or cached_data.get("schemaVersion") != _backend.NORMALIZED_SCHEMA_VERSION
        )
        if previous != fingerprint:
            if timetable_path.exists() and subject_path.exists():
                cached.unlink(missing_ok=True)
            else:
                cache_verified = False

    data = _original_load_or_build_data(college, allow_download=allow_download)
    if cache_verified:
        data["syllabusMappingFingerprint"] = fingerprint
        data["syllabusMappingCacheVerified"] = True
        if needs_write:
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
