"""Operational application bootstrap entry point.

Tactical Satellite Imagery & Reconnaissance Dashboard.

Usage:
    1. pip install -r requirements.txt
    2. Place the custom-trained YOLOv8 Small weights payload at weights/best.pt
    3. python main.py
"""

import os
import sys

# ---------------------------------------------------------------------------
# Path bootstrap: guarantee the project root (this file's directory) is on
# sys.path so the config/, core/, and ui/ packages resolve no matter how the
# script is launched (IDE runner, python -m, different working directory...).
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

for _package in ("config", "core", "ui"):
    if not os.path.isdir(os.path.join(PROJECT_ROOT, _package)):
        raise SystemExit(
            f"Startup failure: the '{_package}\\' folder must sit next to main.py. "
            "Restore the full project structure (config/, core/, ui/, weights/) and retry."
        )

from PyQt6.QtWidgets import QApplication  # noqa: E402

from config import settings  # noqa: E402
from core.database import DatabaseManager  # noqa: E402
from ui.components import load_stylesheet  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def ensure_runtime_layout():
    """Guarantee the weights directory and its placeholder payload exist."""
    os.makedirs(settings.WEIGHTS_DIR, exist_ok=True)
    if not os.path.exists(settings.MODEL_PATH):
        with open(settings.MODEL_PATH, "wb"):
            pass  # Create the empty placeholder; the operator pastes best.pt here.


def main():
    ensure_runtime_layout()
    database = DatabaseManager(settings.DB_PATH)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())

    window = MainWindow(database)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
