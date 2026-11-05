# syntax=docker/dockerfile:1
# Tactical Satellite Imagery & Reconnaissance Dashboard — container image.
#
# This is a PyQt6 GUI application: the container must be launched with access
# to an X11/Wayland display (WSLg on Windows, forwarded X socket on Linux).
# See docker/README.md for the exact launch commands per platform..

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    QT_X11_NO_MITSHM=1 \
    OLLAMA_MODEL=llama3 \
    DISPLAY=:0

WORKDIR /app

# ---- System runtime libraries (Qt6 / PyQt6 + OpenCV + xauth for X11) ------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 libegl1 libglib2.0-0 libdbus-1-3 libfontconfig1 \
        libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
        libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
        libxcb-xinerama0 libxcb-xkb1 libxcb-xfixes0 libxcb1 libx11-6 \
        libxext6 libxrender1 libxi6 libxtst6 libsm6 libice6 libgomp1 \
        fonts-dejavu-core xauth && \
    rm -rf /var/lib/apt/lists/*

# ---- Python dependencies --------------------------------------------------
COPY requirements.txt .

# Install CPU-only PyTorch first so ultralytics does not pull the multi-GB
# CUDA build. Everything else comes from requirements.txt off PyPI.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ---- Application code + trained weights -----------------------------------
COPY main.py ./
COPY config/ ./config/
COPY core/ ./core/
COPY ui/ ./ui/
COPY weights/ ./weights/

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
