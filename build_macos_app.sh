#!/bin/bash
# Build a double-clickable macOS .app with PyInstaller.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv .venv
  PYTHON=".venv/bin/python"
fi

echo "→ Installing build dependencies…"
"$PYTHON" -m pip install -q -r requirements.txt pyinstaller

APP_NAME="YouTube Playlist Downloader"
DIST_DIR="dist"

echo "→ Cleaning previous build…"
rm -rf build "$DIST_DIR/$APP_NAME.app" "$DIST_DIR/$APP_NAME" *.spec

echo "→ Building $APP_NAME.app (this can take a minute)…"
"$PYTHON" -m PyInstaller \
  --noconfirm \
  --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "com.amineaqebli.youtubeplaylistdownloader" \
  --collect-all yt_dlp \
  --collect-all imageio_ffmpeg \
  --collect-all certifi \
  --hidden-import PIL \
  --hidden-import PIL._tkinter_finder \
  --hidden-import imageio_ffmpeg \
  main.py

APP_PATH="$DIST_DIR/$APP_NAME.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "Build failed: $APP_PATH not found"
  exit 1
fi

# Clear quarantine so Gatekeeper is less likely to block first launch.
xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true

echo
echo "✓ Built: $APP_PATH"
echo
echo "Open it with:"
echo "  open \"$APP_PATH\""
echo
echo "Or drag it to Applications / Desktop."
