#!/usr/bin/env bash
# Build the static site and preview it. macOS and Linux.
#   chmod +x build_unix.sh && ./build_unix.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi

if ! "$PY" -c "import openpyxl" >/dev/null 2>&1; then
  echo "Installing required Python packages..."
  "$PY" -m pip install -r requirements.txt
fi

exec "$PY" build_site.py --serve
