from __future__ import annotations

import os
import ssl
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import app_backend as _backend
from app_backend import *  # noqa: F401,F403 - preserve the public API used by tests and scripts


_original_download_file = _backend.download_file
_original_do_GET = _backend.Handler.do_GET
_STATIC_FILES = {
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app-core.js": ("app-core.js", "application/javascript; charset=utf-8"),
    "/app-ui.js": ("app-ui.js", "application/javascript; charset=utf-8"),
    "/app-events.js": ("app-events.js", "application/javascript; charset=utf-8"),
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
