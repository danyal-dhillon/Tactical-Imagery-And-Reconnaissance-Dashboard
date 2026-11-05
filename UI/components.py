"""Customized stylized control widgets and sidebar building blocks."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton

_QSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.qss")

# Minimal fallback theme, used only if styles.qss is unreadable on disk.
_FALLBACK_QSS = (
    "QMainWindow, QWidget { background-color: #121414; color: #E1E4E4; }"
    "QGroupBox, QTableWidget, QListWidget, QLabel#statusLabel {"
    "  background-color: #1A1D1D; border: 1px solid #2E3434; }"
    "QPushButton { background-color: #1A1D1D; border: 1px solid #2E3434;"
    "  padding: 8px 10px; color: #E1E4E4; font-weight: bold; }"
    "QLineEdit, QComboBox { background-color: #121414; border: 1px solid #2E3434;"
    "  padding: 5px; color: #E1E4E4; }"
    "QLabel#panelTitle { color: #E74C3C; font-weight: bold; }"
    "QLabel#displayCanvas { background-color: #0B0D0D; border: 2px solid #2E3434; }"
)


def load_stylesheet():
    """Read ui/styles.qss from disk, falling back to a built-in minimal theme."""
    try:
        with open(_QSS_PATH, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return _FALLBACK_QSS


class PanelTitle(QLabel):
    """Red section banner label used to head each tactical control zone."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("panelTitle")


class FieldLabel(QLabel):
    """Muted caption label placed above input fields."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("fieldLabel")


class FieldNote(QLabel):
    """Small helper note rendered under configuration inputs."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("fieldNote")
        self.setWordWrap(True)


class StatusLabel(QLabel):
    """Framed status readout strip at the foot of the control panel."""

    def __init__(self, text="SYSTEM READY - AWAITING TASKING", parent=None):
        super().__init__(text, parent)
        self.setObjectName("statusLabel")
        self.setWordWrap(True)


class TacticalButton(QPushButton):
    """Standard operation button; pass variant='engage' for the alert-red style."""

    def __init__(self, text, variant="default", parent=None):
        super().__init__(text, parent)
        if variant == "engage":
            self.setObjectName("engageButton")


class TechIntButton(QPushButton):
    """Compact per-row button embedded in the threat tracker table."""

    def __init__(self, parent=None):
        super().__init__("VIEW", parent)
        self.setObjectName("techintButton")


class ApiKeyField(QLineEdit):
    """Password-masked credential input for Tier 2 API configuration."""

    def __init__(self, value="", placeholder="", parent=None):
        super().__init__(value, parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        if placeholder:
            self.setPlaceholderText(placeholder)


class SectionDivider(QFrame):
    """Horizontal rule separating tracker zones."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionDivider")
        self.setFrameShape(QFrame.Shape.HLine)


class DisplayCanvas(QLabel):
    """Framed vision canvas rendering the annotated detection stream."""

    def __init__(self, parent=None):
        super().__init__("NO SIGNAL", parent)
        self.setObjectName("displayCanvas")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 320)
