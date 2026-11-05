"""Operational application bootstrap entry point.

Tactical Satellite Imagery & Reconnaissance Dashboard.

Usage:
    1. pip install -r requirements.txt
    2. Place the custom-trained YOLOv8 Small weights payload at weights/best.pt
    3. python main.py
"""

import os
import sys

from PyQt6.QtWidgets import QApplication

from config import settings
from core.database import DatabaseManager
from ui.components import load_stylesheet
from ui.main_window import MainWindow


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
