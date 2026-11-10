"""FTTR quality classification and ODF detection in one Label Studio response."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from ultralytics import YOLO

from common import resolve_local_image, yolo_box_result


class FTTRQualityAndODF(LabelStudioMLBase):
    IMAGE_KEY = "image"
    QUALITY_FROM_NAME = "quality"
    DETECTOR_FROM_NAME = "object"
    TO_NAME = "image"
    DEFAULT_ROOT = Path(__file__).resolve().parents[3]
    # Match the active Splitter labeling schema. `fiber_cable` is intentionally
    # omitted: the model may detect it, but it is not a label the team reviews.
    ALLOWED_DETECTION_LABELS = {
        "cabinet", "cabinet_label", "tidy_cable", "messy_cable", "label_tag", "foreign_object",
    }

    def setup(self) -> None:
        classifier_path = Path(os.getenv("CLASSIFICATION_MODEL_PATH", "")).expanduser().resolve()
        detector_path = Path(os.getenv("DETECTION_MODEL_PATH", "")).expanduser().resolve()
        if not classifier_path.is_file() or not detector_path.is_file():
            raise FileNotFoundError("Set valid CLASSIFICATION_MODEL_PATH and DETECTION_MODEL_PATH")
        self.confidence = float(os.getenv("YOLO_CONF", "0.25"))
        self.image_size = int(os.getenv("YOLO_IMGSZ", "640"))
        self.device = os.getenv("YOLO_DEVICE") or None
        self.class_map = {str(k): v for k, v in json.loads(os.getenv("QUALITY_LABEL_MAP", "{}")).items()}
        self.detect_map = {str(k): v for k, v in json.loads(os.getenv("LABEL_MAP", "{}")).items()}
        self.classifier = YOLO(str(classifier_path))
        self.detector = YOLO(str(detector_path))
        self.set("model_version", f"fttr-odf:{classifier_path.name}+{detector_path.name}")

    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> ModelResponse:
        predictions = []
        for task in tasks:
            image_path = resolve_local_image(task, self.IMAGE_KEY, self.DEFAULT_ROOT)
            args = {"source": str(image_path), "imgsz": self.image_size, "verbose": False}
            if self.device:
                args["device"] = self.device
            classified = self.classifier.predict(**args)[0]
            detected = self.detector.predict(conf=self.confidence, **args)[0]
            height, width = detected.orig_shape
            regions, scores = [], []
            if classified.probs is not None:
                class_id = int(classified.probs.top1)
                raw_label = str(self.classifier.names[class_id])
                label = self.class_map.get(str(class_id), self.class_map.get(raw_label, raw_label))
                score = float(classified.probs.top1conf.item())
                regions.append({"id": uuid4().hex[:10], "from_name": self.QUALITY_FROM_NAME,
                    "to_name": self.TO_NAME, "type": "choices", "score": score,
                    "value": {"choices": [label]}})
                scores.append(score)
            if detected.boxes is not None:
                for box in detected.boxes:
                    class_id = int(box.cls.item())
                    label = self.detect_map.get(str(class_id), str(self.detector.names[class_id]))
                    if label not in self.ALLOWED_DETECTION_LABELS:
                        continue

                    score = float(box.conf.item())
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    regions.append(yolo_box_result(region_id=uuid4().hex[:10], from_name=self.DETECTOR_FROM_NAME,
                        to_name=self.TO_NAME, label=label, score=score, x1=x1, y1=y1, x2=x2, y2=y2,
                        width=width, height=height))
                    scores.append(score)
            predictions.append({"result": regions, "score": sum(scores) / len(scores) if scores else 0.0,
                                "model_version": self.model_version})
        return ModelResponse(predictions=predictions)

    def fit(self, event, data, **kwargs):
        return {"status": "prediction-only", "event": event}
