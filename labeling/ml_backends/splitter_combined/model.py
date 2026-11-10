"""One-pass Splitter prelabeler: FTTH/SP, FTTR quality/ODF, and metadata boxes."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from ultralytics import YOLO
from common import resolve_local_image, yolo_box_result


class SplitterCombined(LabelStudioMLBase):
    ROOT = Path(__file__).resolve().parents[3]
    IMAGE_KEY, FROM_NAME, QUALITY_FROM, TO_NAME = "image", "object", "quality", "image"
    FTTH_ALLOWED = {"SP2_Correct", "SP2_Incorrect_Unclear", "SP_Open", "SP_Close", "nameplate", "Fast_Connector", "Connector_Correct", "Connector_Wrong_Type"}
    ODF_ALLOWED = {"cabinet", "cabinet_label", "tidy_cable", "messy_cable", "label_tag", "foreign_object"}

    def setup(self) -> None:
        paths = {
            "ftth": Path(os.getenv("FTTH_MODEL_PATH", str(self.ROOT / "Splitter" / "models" / "ftth" / "best.pt"))).resolve(),
            "classifier": Path(os.getenv("CLASSIFICATION_MODEL_PATH", str(self.ROOT / "Splitter" / "models" / "fttr" / "classification_baseline.pt"))).resolve(),
            "odf": Path(os.getenv("DETECTION_MODEL_PATH", str(self.ROOT / "Splitter" / "models" / "fttr" / "detection_yolo26s_7class_640v1_production.pt"))).resolve(),
            "metadata": Path(os.getenv("METADATA_MODEL_PATH", str(self.ROOT / "lat-long" / "models" / "best.pt"))).resolve(),
        }
        if not all(path.is_file() for path in paths.values()):
            raise FileNotFoundError(f"Combined Splitter model missing: {paths}")
        self.confidence, self.image_size = float(os.getenv("YOLO_CONF", "0.25")), int(os.getenv("YOLO_IMGSZ", "640"))
        self.device = os.getenv("YOLO_DEVICE") or None
        self.ftth, self.classifier, self.odf, self.metadata = (YOLO(str(paths[key])) for key in ("ftth", "classifier", "odf", "metadata"))
        self.set("model_version", "splitter-combined")

    def _predict(self, model: YOLO, image_path: Path, *, confidence: bool = True):
        args = {"source": str(image_path), "imgsz": self.image_size, "verbose": False}
        if confidence: args["conf"] = self.confidence
        if self.device: args["device"] = self.device
        return model.predict(**args)[0]

    def _boxes(self, output, allowed: set[str], regions: list, scores: list) -> None:
        if output.boxes is None: return
        height, width = output.orig_shape
        for box in output.boxes:
            label = str(output.names[int(box.cls.item())])
            if label not in allowed: continue
            score = float(box.conf.item()); x1, y1, x2, y2 = box.xyxy[0].tolist()
            regions.append(yolo_box_result(region_id=uuid4().hex[:10], from_name=self.FROM_NAME, to_name=self.TO_NAME,
                label=label, score=score, x1=x1, y1=y1, x2=x2, y2=y2, width=width, height=height)); scores.append(score)

    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> ModelResponse:
        predictions = []
        for task in tasks:
            image_path = resolve_local_image(task, self.IMAGE_KEY, self.ROOT)
            ftth, quality, odf, metadata = (self._predict(model, image_path, confidence=model is not self.classifier)
                                            for model in (self.ftth, self.classifier, self.odf, self.metadata))
            regions, scores = [], []
            self._boxes(ftth, self.FTTH_ALLOWED, regions, scores)
            self._boxes(odf, self.ODF_ALLOWED, regions, scores)
            self._boxes(metadata, {"lat-long", "datetime"}, regions, scores)
            has_cabinet = odf.boxes is not None and any(
                str(odf.names[int(box.cls.item())]) == "cabinet" for box in odf.boxes
            )
            if has_cabinet and quality.probs is not None:
                class_id = int(quality.probs.top1)
                score = float(quality.probs.top1conf.item())
                label = str(quality.names[class_id])
            else:
                # The quality classifier is meaningful only for detected ODF cabinets.
                label = "NotApplicable"
                score = 1.0 if not has_cabinet else 0.0
            regions.append({"id": uuid4().hex[:10], "from_name": self.QUALITY_FROM,
                "to_name": self.TO_NAME, "type": "choices", "score": score,
                "value": {"choices": [label]}})
            scores.append(score)
            predictions.append({"result": regions, "score": sum(scores) / len(scores) if scores else 0.0,
                                "model_version": self.model_version})
        return ModelResponse(predictions=predictions)

    def fit(self, event, data, **kwargs): return {"status": "prediction-only", "event": event}
