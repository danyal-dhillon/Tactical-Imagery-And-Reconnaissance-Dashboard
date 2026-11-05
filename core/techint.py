"""Hybrid Spec-Router: Tier 1 SQLite dictionary lookups, Tier 2 LLM API fallback."""

import json
import urllib.error
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

from config import settings


def record_to_text(record):
    """Format a Tier 1 TechInt record as a single analyst-readable string."""
    if record is None:
        return (
            "Estimated Manufacturer: Unknown | Primary Role: Unclassified Hardware Asset | "
            "Threat Assessment: UNDETERMINED"
        )
    return (
        f"Estimated Manufacturer: {record['manufacturer']} | "
        f"Primary Role: {record['role']} | "
        f"Threat Assessment: {record['assessment']}"
    )


class TechIntRouter:
    """Tiered lookup engine. Never raises - always returns usable analyst text."""

    def __init__(self, database, gemini_key="", openai_key="", ollama_url=""):
        self.database = database
        self.gemini_key = gemini_key.strip()
        self.openai_key = openai_key.strip()
        self.ollama_url = ollama_url.strip()

    @staticmethod
    def build_prompt(class_name):
        return (
            f"You are a defense intelligence analyst. For the asset class '{class_name}' "
            "detected in satellite or aerial imagery, give three short plain-text lines: "
            "Estimated Manufacturer, Primary Role, Threat Assessment Level. No markdown."
        )

    def lookup(self, class_name):
        """Return (text, source_label). Tier 1 SQLite first, Tier 2 LLM hooks second."""
        tier1_text = record_to_text(self.database.get_techint(class_name))
        providers = self.available_providers()
        if not providers:
            return tier1_text, "TIER 1 - LOCAL TECHINT DATABASE"

        prompt = self.build_prompt(class_name)
        failures = []
        for label, handler in providers:
            try:
                answer = handler(prompt)
                if answer:
                    return answer.strip(), f"TIER 2 - {label}"
                failures.append(f"{label}: empty response")
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError, OSError) as error:
                failures.append(f"{label}: {error}")

        note = "; ".join(failures)
        return tier1_text, f"TIER 1 - LOCAL TECHINT DATABASE (Tier 2 unavailable: {note})"

    def available_providers(self):
        providers = []
        if self.gemini_key:
            providers.append(("GEMINI API", self._query_gemini))
        if self.openai_key:
            providers.append(("OPENAI API", self._query_openai))
        if self.ollama_url:
            providers.append(("LOCAL OLLAMA", self._query_ollama))
        return providers

    @staticmethod
    def _post_json(url, payload, headers):
        data = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json"}
        request_headers.update(headers)
        request = urllib.request.Request(url, data=data, headers=request_headers, method="POST")
        with urllib.request.urlopen(request, timeout=settings.LLM_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def _query_gemini(self, prompt):
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        result = self._post_json(
            settings.GEMINI_ENDPOINT, payload, {"x-goog-api-key": self.gemini_key}
        )
        return result["candidates"][0]["content"]["parts"][0]["text"]

    def _query_openai(self, prompt):
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        result = self._post_json(
            settings.OPENAI_ENDPOINT, payload, {"Authorization": f"Bearer {self.openai_key}"}
        )
        return result["choices"][0]["message"]["content"]

    def _query_ollama(self, prompt):
        payload = {"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
        result = self._post_json(self.ollama_url, payload, {})
        return result["response"]


class TechIntThread(QThread):
    """Runs the (potentially slow) TechInt lookup off the UI thread."""

    lookup_complete = pyqtSignal(str, str, str)

    def __init__(self, router, class_name, parent=None):
        super().__init__(parent)
        self.router = router
        self.class_name = class_name

    def run(self):
        text, source = self.router.lookup(self.class_name)
        self.lookup_complete.emit(self.class_name, text, source)
