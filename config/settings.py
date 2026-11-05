"""Central configuration: UI palette, class schema, thresholds, and API endpoints."""

import os

# ---------------------------------------------------------------------------
# Filesystem locations (project root is the directory above this package)
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")
MODEL_PATH = os.path.join(WEIGHTS_DIR, "best.pt")
DB_PATH = os.path.join(BASE_DIR, "tactical_intel.db")

# ---------------------------------------------------------------------------
# Core schema: class ID mappings and detection policy
# ---------------------------------------------------------------------------

CLASS_NAMES = {
    0: "Fighter-Transport_Aircraft",
    1: "Naval_Combatant",
    2: "Armored_Vehicle",
    3: "Air_Defense_System",
    4: "Strategic_Facility",
}

DEFAULT_CONFIDENCE = 0.50
MAX_LIVE_TABLE_ROWS = 60
DB_FLUSH_BATCH = 100
PDF_DETAIL_ROWS = 30

# ---------------------------------------------------------------------------
# Dark tactical military combat UI palette
# ---------------------------------------------------------------------------

COLOR_BACKGROUND = "#121414"
COLOR_SURFACE = "#1A1D1D"
COLOR_ACCENT = "#2E3434"
COLOR_TEXT = "#E1E4E4"
COLOR_ALERT = "#E74C3C"

# ---------------------------------------------------------------------------
# Ingestion and reporting parameters
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".wmv")

DISCLAIMER_TEXT = "This is for informational purposes only. AI responses may include mistakes."

# ---------------------------------------------------------------------------
# Tier 2 TechInt API endpoint configuration
# ---------------------------------------------------------------------------

OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
LLM_TIMEOUT_SECONDS = 15

THREAT_LEVEL_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}

# ---------------------------------------------------------------------------
# Tier 1 unclassified TechInt dictionary (seeded into SQLite at boot)
# ---------------------------------------------------------------------------

TECHINT_DATABASE = {
    "Fighter-Transport_Aircraft": {
        "manufacturer": "Lockheed Martin / Boeing",
        "role": "Air Superiority / Strategic Airlift",
        "assessment": "HIGH - Rapid force projection and airspace contestation capability",
    },
    "Naval_Combatant": {
        "manufacturer": "Huntington Ingalls / BAE Systems / General Dynamics",
        "role": "Surface Warfare / Fleet Escort / Sea Control",
        "assessment": "HIGH - Maritime strike and area-denial platform",
    },
    "Armored_Vehicle": {
        "manufacturer": "General Dynamics Land Systems / Rheinmetall / BAE Systems",
        "role": "Armored Maneuver / Direct Fire Support",
        "assessment": "HIGH - Mobile ground combat and breakthrough capability",
    },
    "Air_Defense_System": {
        "manufacturer": "Raytheon Technologies / Almaz-Antey / MBDA",
        "role": "Integrated Air and Missile Defense",
        "assessment": "CRITICAL - Denies air access and threatens friendly aviation assets",
    },
    "Strategic_Facility": {
        "manufacturer": "State Infrastructure / Undisclosed Contractors",
        "role": "Command, Logistics, Industrial or Strategic Support Node",
        "assessment": "MEDIUM - High-value fixed node, relevant for targeting prioritization",
    },
}


def threat_level_for_class(class_id):
    """Map a class ID to its operational threat level."""
    if class_id == 3:
        return "CRITICAL"
    if class_id in (0, 1, 2):
        return "HIGH"
    if class_id == 4:
        return "MEDIUM"
    return "MEDIUM"


def threat_level_for_name(class_name):
    """Map a class name to its operational threat level."""
    for class_id, name in CLASS_NAMES.items():
        if name == class_name:
            return threat_level_for_class(class_id)
    return "MEDIUM"
