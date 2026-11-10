"""YOLO detection for latitude/longitude and timestamp regions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from ultralytics import YOLO

from common import resolve_local_image, yolo_box_result


class MetadataOCR(LabelStudioMLBase):
    # Safety uses metadata_box; Splitter uses object. Configure this per
    # backend process instead of emitting results for the wrong control tag.
    FROM_NAME = os.getenv("LS_FROM_NAME", "object")
    TO_NAME = os.getenv("LS_TO_NAME", "image")
    IMAGE_KEY = os.getenv("LS_IMAGE_KEY", "image")
    DEFAULT_ROOT = Path(__file__).resolve().parents[3]
    DEFAULT_MODEL = DEFAULT_ROOT / "lat-long" / "models" / "best.pt"

    def setup(self) -> None:
        model_path = Path(os.getenv("METADATA_MODEL_PATH", str(self.DEFAULT_MODEL))).expanduser().resolve()
        if not model_path.is_file():
            raise FileNotFoundError(f"Metadata model not found: {model_path}")
        self.confidence = float(os.getenv("METADATA_CONF", "0.25"))
        self.image_size = int(os.getenv("METADATA_IMGSZ", "1280"))
        self.device = os.getenv("YOLO_DEVICE") or None
        self.model = YOLO(str(model_path))
        self.set("model_version", f"metadata-detector:{model_path.name}")

    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> ModelResponse:
        predictions = []
        for task in tasks:
            image_path = resolve_local_image(task, self.IMAGE_KEY, self.DEFAULT_ROOT)
            args = {"source": str(image_path), "conf": self.confidence, "imgsz": self.image_size, "verbose": False}
            if self.device:
                args["device"] = self.device
            output = self.model.predict(**args)[0]
            height, width = output.orig_shape
            regions = []
            scores = []
            if output.boxes is not None:
                for box in output.boxes:
                    class_id = int(box.cls.item())
                    label = str(self.model.names[class_id])
                    score = float(box.conf.item())
                    x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                    regions.append(yolo_box_result(region_id=uuid4().hex[:10], from_name=self.FROM_NAME,
                        to_name=self.TO_NAME, label=label, score=score, x1=x1, y1=y1, x2=x2, y2=y2,
                        width=width, height=height))
                    scores.append(score)
            predictions.append({"result": regions, "score": sum(scores) / len(scores) if scores else 0.0,
                                "model_version": self.model_version})
        return ModelResponse(predictions=predictions)

    def fit(self, event, data, **kwargs):
        return {"status": "prediction-only", "event": event}
