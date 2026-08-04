#!/bin/bash
# Double-click this file in Finder to start the app.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON=""
if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  osascript -e 'display dialog "Python 3 is required.\nInstall from https://www.python.org/downloads/ then try again." buttons {"OK"} default button 1 with title "YouTube Playlist Downloader"'
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Creating virtual environment…"
  "$PYTHON" -m venv .venv
  PYTHON=".venv/bin/python"
fi

echo "Checking dependencies…"
"$PYTHON" -m pip install -q -r requirements.txt

exec "$PYTHON" main.py
