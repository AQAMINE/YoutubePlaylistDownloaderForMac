FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Default save path inside the container (mount a host folder over this)
    YTPD_SAVE_PATH=/downloads

WORKDIR /app

# FFmpeg for audio/video merge; Tk + X11 libs for the desktop GUI
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    python3-tk \
    tk \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxft2 \
    libfreetype6 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /downloads

# GUI needs a display (e.g. XQuartz on macOS + -e DISPLAY=host.docker.internal:0).
# For everyday use on Mac, prefer the .app / .command launcher instead.
CMD ["python", "main.py"]
