"""Decoupled QThread worker running OpenCV capture and the YOLOv8 model."""

import os
import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage
from ultralytics import YOLO

from config import settings


class VideoProcessingThread(QThread):
    """Capture + YOLOv8 inference worker, decoupled from the UI thread."""

    frame_processed = pyqtSignal(QImage)
    detections_logged = pyqtSignal(list)
    status_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, source_path, parent=None):
        super().__init__(parent)
        self.source_path = str(source_path).strip()
        self._running = True

    def stop(self):
        self._running = False

    def _is_live_source(self):
        return self.source_path.isdigit()

    def _is_still_image(self):
        return self.source_path.lower().endswith(settings.IMAGE_EXTENSIONS)

    @staticmethod
    def _to_qimage(bgr_frame):
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        height, width, channels = rgb.shape
        image = QImage(rgb.data, width, height, channels * width, QImage.Format.Format_RGB888)
        return image.copy()

    @staticmethod
    def _extract_detections(result, model_names):
        detections = []
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return detections
        class_ids = boxes.cls.cpu().numpy().astype(int).tolist()
        confidences = boxes.conf.cpu().numpy().astype(float).tolist()
        for class_id, confidence in zip(class_ids, confidences):
            class_name = settings.CLASS_NAMES.get(
                class_id, str(model_names.get(class_id, f"Class_{class_id}"))
            )
            detections.append(
                {"class_id": int(class_id), "class_name": class_name, "confidence": float(confidence)}
            )
        return detections

    def run(self):
        capture = None
        try:
            if not os.path.exists(settings.MODEL_PATH) or os.path.getsize(settings.MODEL_PATH) == 0:
                self.error_occurred.emit(
                    f"Model weights not installed: place your trained YOLOv8 payload at {settings.MODEL_PATH}"
                )
                return

            if not self._is_live_source() and not os.path.exists(self.source_path):
                self.error_occurred.emit(f"Source file not found: {self.source_path}")
                return

            source = int(self.source_path) if self._is_live_source() else self.source_path
            capture = cv2.VideoCapture(source)
            if not capture.isOpened():
                self.error_occurred.emit(f"Unable to open source: {self.source_path}")
                return

            self.status_message.emit("Loading YOLOv8 model...")
            model = YOLO(settings.MODEL_PATH)
            self.status_message.emit("RECON FEED ACTIVE")

            source_fps = capture.get(cv2.CAP_PROP_FPS)
            frame_interval = 0.0
            if not self._is_live_source() and not self._is_still_image() and source_fps and source_fps > 1:
                frame_interval = 1.0 / source_fps

            while self._running:
                loop_start = time.perf_counter()
                grabbed, frame = capture.read()
                if not grabbed or frame is None:
                    break

                results = model.predict(frame, conf=settings.DEFAULT_CONFIDENCE, verbose=False)
                result = results[0]
                annotated = result.plot()

                self.frame_processed.emit(self._to_qimage(annotated))
                self.detections_logged.emit(self._extract_detections(result, model.names))

                if frame_interval > 0:
                    remaining = frame_interval - (time.perf_counter() - loop_start)
                    if remaining > 0:
                        self.msleep(int(remaining * 1000))

            self.status_message.emit("RECON FEED TERMINATED")
        except Exception as error:  # noqa: BLE001 - worker must never crash the UI process
            self.error_occurred.emit(f"Processing failure: {error}")
        finally:
            if capture is not None:
                capture.release()
