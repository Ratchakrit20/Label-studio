"""Configurable YOLO detector for Label Studio rectangle pre-annotations."""

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


class YOLODetector(LabelStudioMLBase):
    FROM_NAME = os.getenv("LS_FROM_NAME", "object")
    TO_NAME = os.getenv("LS_TO_NAME", "image")
    IMAGE_KEY = os.getenv("LS_IMAGE_KEY", "image")
    DEFAULT_ROOT = Path(__file__).resolve().parents[3]
    # These are the FTTH classes exposed by Splitter/label_config.xml.
    # The checkpoint also knows `pole` and `SP_Damaged`; do not return them
    # because the active labeling schema intentionally does not include them.
    DEFAULT_ALLOWED_LABELS = {
        "SP2_Correct", "SP2_Incorrect_Unclear", "SP_Open", "SP_Close",
        "nameplate", "Fast_Connector", "Connector_Correct", "Connector_Wrong_Type",
    }

    def setup(self) -> None:
        value = os.getenv("YOLO_MODEL_PATH")
        if not value:
            raise RuntimeError("Set YOLO_MODEL_PATH before starting this backend")
        model_path = Path(value).expanduser().resolve()
        if not model_path.is_file():
            raise FileNotFoundError(f"YOLO model not found: {model_path}")
        self.confidence = float(os.getenv("YOLO_CONF", "0.25"))
        self.image_size = int(os.getenv("YOLO_IMGSZ", "640"))
        self.device = os.getenv("YOLO_DEVICE") or None
        self.label_map = {str(k): v for k, v in json.loads(os.getenv("LABEL_MAP", "{}")).items()}
        configured_labels = os.getenv("ALLOWED_LABELS", "")
        self.allowed_labels = (
            {label.strip() for label in configured_labels.split(",") if label.strip()}
            if configured_labels else self.DEFAULT_ALLOWED_LABELS
        )
        self.model = YOLO(str(model_path))
        self.set("model_version", f"yolo-detector:{model_path.name}")

    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> ModelResponse:
        predictions = []
        for task in tasks:
            image_path = resolve_local_image(task, self.IMAGE_KEY, self.DEFAULT_ROOT)
            args = {"source": str(image_path), "conf": self.confidence, "imgsz": self.image_size, "verbose": False}
            if self.device:
                args["device"] = self.device
            output = self.model.predict(**args)[0]
            height, width = output.orig_shape
            regions, scores = [], []
            if output.boxes is not None:
                for box in output.boxes:
                    class_id = int(box.cls.item())
                    label = self.label_map.get(str(class_id), str(self.model.names[class_id]))
                    if label not in self.allowed_labels:
                        continue
                    score = float(box.conf.item())
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    regions.append(yolo_box_result(region_id=uuid4().hex[:10], from_name=self.FROM_NAME,
                        to_name=self.TO_NAME, label=label, score=score, x1=x1, y1=y1, x2=x2, y2=y2,
                        width=width, height=height))
                    scores.append(score)
            predictions.append({"result": regions, "score": sum(scores) / len(scores) if scores else 0.0,
                                "model_version": self.model_version})
        return ModelResponse(predictions=predictions)

    def fit(self, event, data, **kwargs):
        return {"status": "prediction-only", "event": event}
