# YouTube Playlist Downloader

Python desktop app to download YouTube videos, playlists, and channels. Works on macOS (and Linux/Windows with Python).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

FFmpeg is included via `imageio-ffmpeg` (needed to merge video + audio).

## Run

```bash
source .venv/bin/activate
python main.py
```

## Features

- Download single videos, playlists, or channels
- Video (mp4 / mkv / webm) or audio-only (mp3, m4a, opus, …)
- Quality selection (best → 144p)
- Playlist index subset (start / end)
- Skip already downloaded files
- Optional subfolder per playlist
- Progress, speed, and log panel

Downloads default to `~/Downloads/YouTubeDownloads`.

## License

Free and open source (MIT) — developed by **Amine Aqebli**  
Ingénierie Full Stack et Architecture Logicielle  
See [LICENSE](LICENSE).
