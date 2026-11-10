"""One-pass Safety prelabeler: person masks plus lat/long and datetime boxes."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import cv2
import numpy as np
from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from label_studio_sdk.converter.brush import mask2rle
from ultralytics import YOLO

from common import resolve_local_image, yolo_box_result


class SafetyCombined(LabelStudioMLBase):
    ROOT = Path(__file__).resolve().parents[3]
    IMAGE_KEY = "image"
    PERSON_FROM = "label"
    METADATA_FROM = "metadata_box"
    TO_NAME = "image"
    PERSON_MODEL = ROOT / "Savety" / "label_studio_yolo26_person" / "models" / "yolo26s-seg.pt"
    METADATA_MODEL = ROOT / "lat-long" / "models" / "best.pt"

    def setup(self) -> None:
        person_path = Path(os.getenv("PERSON_MODEL_PATH", str(self.PERSON_MODEL))).resolve()
        metadata_path = Path(os.getenv("METADATA_MODEL_PATH", str(self.METADATA_MODEL))).resolve()
        if not person_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError("Set valid PERSON_MODEL_PATH and METADATA_MODEL_PATH")
        self.confidence = float(os.getenv("YOLO_CONF", "0.25"))
        self.image_size = int(os.getenv("YOLO_IMGSZ", "640"))
        self.device = os.getenv("YOLO_DEVICE") or None
        self.person = YOLO(str(person_path))
        self.metadata = YOLO(str(metadata_path))
        self.set("model_version", f"safety-combined:{person_path.name}+{metadata_path.name}")

    def _args(self, image_path: Path) -> Dict:
        args = {"source": str(image_path), "conf": self.confidence, "imgsz": self.image_size, "verbose": False}
        if self.device:
            args["device"] = self.device
        return args

    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> ModelResponse:
        predictions = []
        for task in tasks:
            image_path = resolve_local_image(task, self.IMAGE_KEY, self.ROOT)
            person_output = self.person.predict(classes=[0], retina_masks=True, **self._args(image_path))[0]
            metadata_output = self.metadata.predict(**self._args(image_path))[0]
            regions, scores = [], []
            if person_output.masks is not None and person_output.boxes is not None:
                masks = person_output.masks.data.detach().cpu().numpy()
                for raw_mask, score in zip(masks, person_output.boxes.conf.detach().cpu().tolist()):
                    width, height = int(person_output.orig_shape[1]), int(person_output.orig_shape[0])
                    binary = (raw_mask > 0.5).astype(np.uint8)
                    mask = cv2.resize(binary, (width, height), interpolation=cv2.INTER_NEAREST) * 255
                    regions.append({"id": uuid4().hex[:10], "from_name": self.PERSON_FROM, "to_name": self.TO_NAME,
                        "type": "brushlabels", "score": float(score), "original_width": width, "original_height": height,
                        "image_rotation": 0, "value": {"format": "rle", "rle": mask2rle(mask), "brushlabels": ["person"]}})
                    scores.append(float(score))
            if metadata_output.boxes is not None:
                height, width = metadata_output.orig_shape
                for box in metadata_output.boxes:
                    label = str(self.metadata.names[int(box.cls.item())])
                    if label not in {"lat-long", "datetime"}:
                        continue
                    score = float(box.conf.item())
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    regions.append(yolo_box_result(region_id=uuid4().hex[:10], from_name=self.METADATA_FROM,
                        to_name=self.TO_NAME, label=label, score=score, x1=x1, y1=y1, x2=x2, y2=y2, width=width, height=height))
                    scores.append(score)
            predictions.append({"result": regions, "score": sum(scores) / len(scores) if scores else 0.0,
                                "model_version": self.model_version})
        return ModelResponse(predictions=predictions)

    def fit(self, event, data, **kwargs):
        return {"status": "prediction-only", "event": event}
