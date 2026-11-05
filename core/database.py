"""SQLite connection manager, DDL builders, log writers, and TechInt spec storage."""

import sqlite3

from config import settings


class DatabaseManager:
    """Thread-safe SQLite access layer (one short-lived connection per call)."""

    def __init__(self, db_path=None):
        self.db_path = db_path or settings.DB_PATH
        self.validate_schema()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    # ----- Schema and seed data -------------------------------------------

    def validate_schema(self):
        """Compile the relational schema at boot if it is missing."""
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS intel_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_type TEXT,
                    total_threat_count INTEGER
                );

                CREATE TABLE IF NOT EXISTS intel_detections (
                    detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    class_name TEXT,
                    confidence REAL,
                    threat_level TEXT,
                    FOREIGN KEY(session_id) REFERENCES intel_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS techint_specs (
                    class_name TEXT PRIMARY KEY,
                    manufacturer TEXT,
                    role TEXT,
                    assessment TEXT
                );
                """
            )
            connection.executemany(
                "INSERT OR IGNORE INTO techint_specs (class_name, manufacturer, role, assessment) "
                "VALUES (?, ?, ?, ?)",
                [
                    (class_name, record["manufacturer"], record["role"], record["assessment"])
                    for class_name, record in settings.TECHINT_DATABASE.items()
                ],
            )
            connection.commit()
        finally:
            connection.close()

    # ----- Session and detection writers ----------------------------------

    def create_session(self, source_type):
        connection = self._connect()
        try:
            cursor = connection.execute(
                "INSERT INTO intel_sessions (source_type, total_threat_count) VALUES (?, 0)",
                (source_type,),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def add_detections(self, session_id, detections):
        if not detections:
            return
        rows = [
            (
                session_id,
                item["class_name"],
                float(item["confidence"]),
                settings.threat_level_for_class(int(item["class_id"])),
            )
            for item in detections
        ]
        connection = self._connect()
        try:
            connection.executemany(
                "INSERT INTO intel_detections (session_id, class_name, confidence, threat_level) "
                "VALUES (?, ?, ?, ?)",
                rows,
            )
            connection.commit()
        finally:
            connection.close()

    def finalize_session(self, session_id):
        connection = self._connect()
        try:
            connection.execute(
                "UPDATE intel_sessions SET total_threat_count = "
                "(SELECT COUNT(*) FROM intel_detections WHERE session_id = ?) WHERE session_id = ?",
                (session_id, session_id),
            )
            connection.commit()
        finally:
            connection.close()

    # ----- Readers ----------------------------------------------------------

    def list_sessions(self, limit=200):
        connection = self._connect()
        try:
            cursor = connection.execute(
                "SELECT session_id, timestamp, source_type, total_threat_count "
                "FROM intel_sessions ORDER BY session_id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def get_session(self, session_id):
        connection = self._connect()
        try:
            cursor = connection.execute(
                "SELECT session_id, timestamp, source_type, total_threat_count "
                "FROM intel_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def get_inventory(self, session_id):
        connection = self._connect()
        try:
            cursor = connection.execute(
                "SELECT class_name, threat_level, COUNT(*) AS total, "
                "AVG(confidence) AS avg_conf, MAX(confidence) AS max_conf "
                "FROM intel_detections WHERE session_id = ? "
                "GROUP BY class_name, threat_level "
                "ORDER BY CASE threat_level WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END, "
                "total DESC",
                (session_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def get_top_detections(self, session_id, limit):
        connection = self._connect()
        try:
            cursor = connection.execute(
                "SELECT detection_id, class_name, confidence, threat_level "
                "FROM intel_detections WHERE session_id = ? "
                "ORDER BY confidence DESC, detection_id ASC LIMIT ?",
                (session_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def count_detections(self, session_id):
        connection = self._connect()
        try:
            cursor = connection.execute(
                "SELECT COUNT(*) FROM intel_detections WHERE session_id = ?", (session_id,)
            )
            return int(cursor.fetchone()[0])
        finally:
            connection.close()

    def get_techint(self, class_name):
        """Tier 1 spec lookup from the seeded SQLite TechInt dictionary."""
        connection = self._connect()
        try:
            cursor = connection.execute(
                "SELECT manufacturer, role, assessment FROM techint_specs WHERE class_name = ?",
                (class_name,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            connection.close()
