#!/bin/sh 
set -e

# The dashboard is a PyQt6 GUI and will not start without a display.
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ] && [ "${QT_QPA_PLATFORM:-}" != "offscreen" ]; then
    echo "[entrypoint] WARNING: no DISPLAY detected." >&2
    echo "[entrypoint] This container runs a PyQt6 desktop application and needs X11/Wayland." >&2
    echo "[entrypoint] Linux  : run 'xhost +local:docker' on the host, then export DISPLAY=:0" >&2
    echo "[entrypoint] Windows: launch Docker from WSL2 so WSLg provides the display." >&2
fi

cd /app

# No arguments -> launch the dashboard. Any arguments are passed straight to
# python, e.g. `docker compose run --rm tactical-dashboard -c "import cv2"`.
if [ "$#" -eq 0 ]; then
    set -- main.py
fi

exec python "$@"
