# Docker Deployment — Tactical Satellite Imagery & Reconnaissance Dashboard

Container packaging for the PyQt6 + YOLOv8 tactical reconnaissance workstation.

```
docker/
├── Dockerfile            # Image definition (Python 3.11 slim + CPU PyTorch + Qt6 libs)
├── docker-compose.yml    # Service with display forwarding, env wiring, volume mounts
├── entrypoint.sh         # Launch guard (needs a display) + python passthrough
└── README.md             # This file
```

## What runs where

The application is a **desktop GUI** (PyQt6). The container therefore needs:

1. **A display** — X11 socket or WSLg. Without one the app cannot start.
2. **A bind mount of the repository** — the SQLite database (`tactical_intel.db`)
   and generated PDF briefings are written next to `main.py`, so the whole repo
   is mounted at `/app` to persist them on the host.
3. **The trained weights** — `weights/best.pt` is baked into the image at build
   time (it is part of the repository), and kept live through the bind mount.

## 1. Build the image

From the repository root (requires Docker Desktop / Docker Engine):

```bash
docker compose -f docker/docker-compose.yml build
```

This produces the image `tactical-satellite-intel:latest`.

## 2. Run the container

### Windows (recommended: Docker Desktop + WSL2 / WSLg)

Docker Desktop with the WSL2 backend exposes the WSLg display automatically,
so no extra display setup is needed:

```powershell
docker compose -f docker\docker-compose.yml up
```

### Linux (X11 forwarding)

Allow the container to connect to your X server, then launch:

```bash
xhost +local:docker
DISPLAY=$DISPLAY docker compose -f docker/docker-compose.yml up
```

### Windows (Docker Desktop desktop VM, no WSLg)

Install an X server such as [VcXsrv](https://sourceforge.net/projects/vcxsrv/)
or X410, allow public connections, then:

```powershell
$env:DISPLAY = "host.docker.internal:0"
docker compose -f docker\docker-compose.yml up
```

### macOS

Install an X server (XQuartz), enable "Allow connections from network clients",
then:

```bash
DISPLAY=host.docker.internal:0 docker compose -f docker/docker-compose.yml up
```

## 3. Stop

```bash
docker compose -f docker/docker-compose.yml down
```

Closing the app window inside the container stops the process; `stop_grace_period:
30s` gives the inference `QThread` and TechInt threads time to shut down cleanly..

## Configuration

All Tier 2 TechInt providers are optional (the app always falls back to the
seeded Tier 1 SQLite dictionary). Export them before running compose, or create
a `docker/.env` file:

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | Gemini Tier 2 enrichment | _(empty)_ |
| `OPENAI_API_KEY` | OpenAI Tier 2 enrichment | _(empty)_ |
| `OLLAMA_URL` | Local Ollama endpoint | `http://host.docker.internal:11434/api/generate` |
| `OLLAMA_MODEL` | Ollama model name | `llama3` |
| `DISPLAY` | X display to attach the GUI to | `:0` |

`host.docker.internal` resolves to the host machine inside the container, so a
local `ollama serve` on the host is reachable without extra networking.

## Volumes and artifacts

- `..:/app` — the repository is bind-mounted, so **live code edits, the SQLite
  database, and generated PDF briefings persist on the host**. The image is
  only the runtime environment.
- `/tmp/.X11-unix` — X11 socket for display forwarding.

## Optional integrations (edit `docker-compose.yml`)

- **Analyze media outside the repo** — uncomment the media volume, then enter
  `/media/<file>` as the source path in the FILE mode of the control panel.
- **Live camera streams (Linux hosts)** — uncomment the `devices:` block to
  pass `/dev/video0` through. Camera indices inside the container refer to the
  container's devices, not the host's.
- **GPU acceleration** — the image ships CPU-only PyTorch to stay portable
  (~2.5 GB). For CUDA, rebuild from a CUDA base image, install the matching
  PyTorch wheel, and enable the `deploy.resources.devices` block (requires the
  NVIDIA Container Toolkit).

## One-off commands

The entrypoint passes any arguments straight to `python`, so you can run
diagnostics without launching the GUI:

```bash
docker compose -f docker/docker-compose.yml run --rm tactical-dashboard -c "import cv2, ultralytics; print(cv2.__version__)"
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| App exits immediately, logs mention `QXcbConnection` / `could not connect to display` | No display reached. Use WSL2/WSLg on Windows, or `xhost +local:docker` + `DISPLAY` on Linux, or an X server on macOS/Windows-desktop-VM. |
| `Could not connect to Ollama` | Ollama must be running on the host; the default URL is `http://host.docker.internal:11434/api/generate`. On WSL2 this works out of the box. |
| Detections don't run: "Model weights not installed" | `weights/best.pt` must be non-empty. It is baked into the image at build time; the bind mount keeps the host copy authoritative. |
| Camera won't open in FILE mode | Live camera needs the `devices:` passthrough (Linux hosts only). |
| PDF report not found after closing the save dialog | The PDF is saved through the container's file dialog; with the bind mount it lands on the host in the repository root. |
