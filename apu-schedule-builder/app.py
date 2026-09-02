from __future__ import annotations

from urllib.parse import urlparse

import app_backend as _backend
from app_backend import *  # noqa: F401,F403 - preserve the public API used by tests and scripts


_original_do_GET = _backend.Handler.do_GET
_STATIC_FILES = {
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app-core.js": ("app-core.js", "application/javascript; charset=utf-8"),
    "/app-ui.js": ("app-ui.js", "application/javascript; charset=utf-8"),
    "/app-events.js": ("app-events.js", "application/javascript; charset=utf-8"),
}


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
