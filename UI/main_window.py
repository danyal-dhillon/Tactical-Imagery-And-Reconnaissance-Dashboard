"""Primary PyQt6 MainWindow composition for the tactical recon dashboard."""

import os
import sqlite3
from xml.sax.saxutils import escape

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import settings
from core.engine import VideoProcessingThread
from core.reporters import compile_intel_report
from core.techint import TechIntRouter, TechIntThread
from ui.components import (
    ApiKeyField,
    DisplayCanvas,
    FieldLabel,
    FieldNote,
    PanelTitle,
    SectionDivider,
    StatusLabel,
    TacticalButton,
    TechIntButton,
)


class MainWindow(QMainWindow):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.worker = None
        self.techint_threads = []
        self.active_session_id = None
        self.pending_detections = []
        self.session_detection_total = 0
        self.latest_detections = []
        self.rendered_signature = None
        self.last_image = None

        self.setWindowTitle("TACTICAL SATELLITE IMAGERY & RECONNAISSANCE DASHBOARD")
        self.resize(1680, 920)
        self.setMinimumSize(1200, 700)

        self._build_ui()
        self.refresh_history()

        self.table_timer = QTimer(self)
        self.table_timer.setInterval(200)
        self.table_timer.timeout.connect(self.refresh_threat_table)
        self.table_timer.start()

    # ----- UI construction -------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_control_panel(), 30)
        root_layout.addWidget(self._build_display_panel(), 40)
        root_layout.addWidget(self._build_tracker_panel(), 30)
        self.setCentralWidget(central)

    def _build_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(PanelTitle("// CONTROL PANEL"))

        source_group = QGroupBox("INTELLIGENCE SOURCE")
        source_layout = QVBoxLayout(source_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["FILE (IMAGE / VIDEO)", "LIVE CAMERA STREAM"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        source_layout.addWidget(self.mode_combo)

        file_row = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Path to image or video file")
        self.browse_button = TacticalButton("BROWSE")
        self.browse_button.clicked.connect(self.browse_source_file)
        file_row.addWidget(self.file_input, 1)
        file_row.addWidget(self.browse_button)
        source_layout.addLayout(file_row)

        self.camera_input = QLineEdit("0")
        self.camera_input.setPlaceholderText("Live stream index (e.g. 0)")
        source_layout.addWidget(self.camera_input)
        layout.addWidget(source_group)

        action_group = QGroupBox("OPERATIONS")
        action_layout = QVBoxLayout(action_group)
        self.engage_button = TacticalButton("ENGAGE ANALYSIS FEED", variant="engage")
        self.engage_button.clicked.connect(self.start_analysis)
        self.stop_button = TacticalButton("STOP RECON FEED")
        self.stop_button.clicked.connect(self.stop_analysis)
        self.stop_button.setEnabled(False)
        self.report_button = TacticalButton("COMPILE INTEL REPORT (PDF)")
        self.report_button.clicked.connect(self.export_report)
        action_layout.addWidget(self.engage_button)
        action_layout.addWidget(self.stop_button)
        action_layout.addWidget(self.report_button)
        layout.addWidget(action_group)

        api_group = QGroupBox("SECURE API CONFIGURATION")
        api_layout = QVBoxLayout(api_group)
        self.gemini_input = ApiKeyField(os.environ.get("GEMINI_API_KEY", ""), "Gemini API key")
        self.openai_input = ApiKeyField(os.environ.get("OPENAI_API_KEY", ""), "OpenAI API key")
        self.ollama_input = QLineEdit(os.environ.get("OLLAMA_URL", settings.OLLAMA_DEFAULT_URL))
        self.ollama_input.setPlaceholderText("Ollama endpoint (blank to disable)")
        api_layout.addWidget(FieldLabel("Gemini API Key"))
        api_layout.addWidget(self.gemini_input)
        api_layout.addWidget(FieldLabel("OpenAI API Key"))
        api_layout.addWidget(self.openai_input)
        api_layout.addWidget(FieldLabel("Local Ollama Endpoint"))
        api_layout.addWidget(self.ollama_input)
        api_layout.addWidget(
            FieldNote("Tier 2 lookups fall back to the local TechInt database if unavailable.")
        )
        layout.addWidget(api_group)

        layout.addStretch(1)

        self.status_label = StatusLabel()
        layout.addWidget(self.status_label)

        self.on_mode_changed(0)
        return panel

    def _build_display_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(PanelTitle("// TACTICAL DISPLAY MONITOR"))

        self.display_label = DisplayCanvas()
        self.display_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.display_label, 1)
        return panel

    def _build_tracker_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(PanelTitle("// LIVE THREAT ASSESSMENT TRACKER"))

        self.threat_table = QTableWidget(0, 4)
        self.threat_table.setHorizontalHeaderLabels(["CLASS NAME", "CONFIDENCE", "PRIORITY", "TECHINT"])
        self.threat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.threat_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.threat_table.setAlternatingRowColors(True)
        self.threat_table.verticalHeader().setVisible(False)
        header = self.threat_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.threat_table, 3)

        layout.addWidget(PanelTitle("// SESSION HISTORY"))

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_history_selected)
        layout.addWidget(self.history_list, 2)

        layout.addWidget(SectionDivider())
        return panel

    # ----- Source selection ------------------------------------------------

    def on_mode_changed(self, index):
        is_file = index == 0
        self.file_input.setEnabled(is_file)
        self.browse_button.setEnabled(is_file)
        self.camera_input.setEnabled(not is_file)

    def browse_source_file(self):
        image_pattern = " ".join(f"*{ext}" for ext in settings.IMAGE_EXTENSIONS)
        video_pattern = " ".join(f"*{ext}" for ext in settings.VIDEO_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image or Video",
            settings.BASE_DIR,
            f"Imagery & Video ({image_pattern} {video_pattern});;All Files (*)",
        )
        if path:
            self.file_input.setText(path)

    def resolve_source(self):
        """Return (source_path, source_type) or (None, None) if invalid."""
        if self.mode_combo.currentIndex() == 1:
            index_text = self.camera_input.text().strip()
            if not index_text.isdigit():
                QMessageBox.warning(self, "Invalid Stream Index", "Enter a numeric camera index such as 0.")
                return None, None
            return index_text, "LIVE_CAMERA"

        path = self.file_input.text().strip()
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "Invalid Source", "Select an existing image or video file.")
            return None, None
        source_type = "IMAGE" if path.lower().endswith(settings.IMAGE_EXTENSIONS) else "VIDEO"
        return path, source_type

    # ----- Analysis lifecycle ---------------------------------------------

    def start_analysis(self):
        if self.worker is not None and self.worker.isRunning():
            return
        source_path, source_type = self.resolve_source()
        if source_path is None:
            return

        self.active_session_id = self.database.create_session(source_type)
        self.pending_detections = []
        self.session_detection_total = 0
        self.latest_detections = []
        self.rendered_signature = None
        self.refresh_history()
        self.select_history_session(self.active_session_id)

        self.worker = VideoProcessingThread(source_path, self)
        self.worker.frame_processed.connect(self.on_frame_processed)
        self.worker.detections_logged.connect(self.on_detections_logged)
        self.worker.status_message.connect(self.set_status)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.finished.connect(self.on_worker_finished)

        self.engage_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.report_button.setEnabled(False)
        self.set_status(f"SESSION #{self.active_session_id} ENGAGED - {source_type}")
        self.worker.start()

    def stop_analysis(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.set_status("STOPPING RECON FEED...")

    def on_worker_finished(self):
        if self.active_session_id is not None:
            self.flush_pending_detections()
            self.database.finalize_session(self.active_session_id)
        self.engage_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.report_button.setEnabled(True)
        self.refresh_history()
        if self.active_session_id is not None:
            self.select_history_session(self.active_session_id)
            self.set_status(
                f"SESSION #{self.active_session_id} COMPLETE - {self.session_detection_total} DETECTIONS LOGGED"
            )

    def on_worker_error(self, message):
        self.set_status(f"ERROR: {message}")
        QMessageBox.critical(self, "Recon Feed Error", message)

    def set_status(self, message):
        self.status_label.setText(message)

    # ----- Frame and detection handling -----------------------------------

    def on_frame_processed(self, image):
        self.last_image = image
        self.render_current_frame()

    def render_current_frame(self):
        if self.last_image is None:
            return
        pixmap = QPixmap.fromImage(self.last_image)
        scaled = pixmap.scaled(
            self.display_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.display_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.render_current_frame()

    def on_detections_logged(self, detections):
        self.latest_detections = detections
        if not detections or self.active_session_id is None:
            return
        self.pending_detections.extend(detections)
        self.session_detection_total += len(detections)
        if len(self.pending_detections) >= settings.DB_FLUSH_BATCH:
            self.flush_pending_detections()

    def flush_pending_detections(self):
        if self.active_session_id is None or not self.pending_detections:
            return
        self.database.add_detections(self.active_session_id, self.pending_detections)
        self.pending_detections = []

    def refresh_threat_table(self):
        detections = self.latest_detections[: settings.MAX_LIVE_TABLE_ROWS]
        signature = tuple((item["class_id"], round(item["confidence"], 2)) for item in detections)
        if signature == self.rendered_signature:
            return
        self.rendered_signature = signature

        ordered = sorted(
            detections,
            key=lambda item: (
                settings.THREAT_LEVEL_ORDER[settings.threat_level_for_class(item["class_id"])],
                -item["confidence"],
            ),
        )
        self.threat_table.setUpdatesEnabled(False)
        self.threat_table.setRowCount(len(ordered))
        for row, item in enumerate(ordered):
            level = settings.threat_level_for_class(item["class_id"])
            name_item = QTableWidgetItem(item["class_name"])
            confidence_item = QTableWidgetItem(f"{item['confidence'] * 100:.1f}%")
            level_item = QTableWidgetItem(level)
            if level == "CRITICAL":
                for cell_item in (name_item, confidence_item, level_item):
                    cell_item.setForeground(QColor(settings.COLOR_ALERT))
            self.threat_table.setItem(row, 0, name_item)
            self.threat_table.setItem(row, 1, confidence_item)
            self.threat_table.setItem(row, 2, level_item)

            button = TechIntButton()
            button.clicked.connect(lambda _checked=False, name=item["class_name"]: self.request_techint(name))
            self.threat_table.setCellWidget(row, 3, button)
        self.threat_table.setUpdatesEnabled(True)

    # ----- TechInt ---------------------------------------------------------

    def request_techint(self, class_name):
        router = TechIntRouter(
            self.database,
            self.gemini_input.text(),
            self.openai_input.text(),
            self.ollama_input.text(),
        )
        self.set_status(f"QUERYING TECHINT: {class_name}")
        thread = TechIntThread(router, class_name, self)
        thread.lookup_complete.connect(self.show_techint)
        thread.finished.connect(lambda t=thread: self.release_techint_thread(t))
        self.techint_threads.append(thread)
        thread.start()

    def release_techint_thread(self, thread):
        if thread in self.techint_threads:
            self.techint_threads.remove(thread)
        thread.deleteLater()

    def show_techint(self, class_name, text, source):
        level = settings.threat_level_for_name(class_name)
        self.set_status(f"TECHINT READY: {class_name}")
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle(f"TechInt - {class_name}")
        message.setText(f"<b>{escape(class_name)}</b><br>Threat Priority: {escape(level)}")
        message.setInformativeText(text.replace(" | ", "\n"))
        message.setDetailedText(f"Source: {source}\n\n{settings.DISCLAIMER_TEXT}")
        message.exec()

    # ----- History and reporting ------------------------------------------

    def refresh_history(self):
        self.history_list.clear()
        for session in self.database.list_sessions():
            label = (
                f"SESSION #{session['session_id']} | {session['timestamp']} | "
                f"{session['source_type']} | THREATS: {session['total_threat_count']}"
            )
            entry = QListWidgetItem(label)
            entry.setData(Qt.ItemDataRole.UserRole, int(session["session_id"]))
            self.history_list.addItem(entry)

    def select_history_session(self, session_id):
        for index in range(self.history_list.count()):
            entry = self.history_list.item(index)
            if entry.data(Qt.ItemDataRole.UserRole) == session_id:
                self.history_list.setCurrentItem(entry)
                return

    def on_history_selected(self, entry):
        session_id = entry.data(Qt.ItemDataRole.UserRole)
        if self.worker is not None and self.worker.isRunning():
            self.set_status("FEED ACTIVE - REPORT TARGETS THE LIVE SESSION UNTIL STOPPED")
            return
        self.active_session_id = int(session_id)
        self.set_status(f"SESSION #{self.active_session_id} SELECTED FOR REPORTING")

    def export_report(self):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Feed Active", "Stop the recon feed before compiling the report.")
            return
        if self.active_session_id is None:
            QMessageBox.information(self, "No Session", "Run or select an analysis session first.")
            return

        session_id = self.active_session_id
        default_path = os.path.join(
            settings.BASE_DIR, f"tactical_briefing_session_{session_id}.pdf"
        )
        output_path, _ = QFileDialog.getSaveFileName(self, "Save Intel Report", default_path, "PDF Files (*.pdf)")
        if not output_path:
            return
        try:
            compile_intel_report(self.database, session_id, output_path)
        except (OSError, ValueError, sqlite3.Error) as error:
            QMessageBox.critical(self, "Report Failure", f"Unable to compile report: {error}")
            return
        self.set_status(f"REPORT SAVED: {output_path}")
        QMessageBox.information(self, "Report Compiled", f"Intelligence briefing saved to:\n{output_path}")

    # ----- Shutdown --------------------------------------------------------

    def closeEvent(self, event):
        self.table_timer.stop()
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(8000)
        for thread in list(self.techint_threads):
            thread.wait(settings.LLM_TIMEOUT_SECONDS * 1000)
        super().closeEvent(event)
