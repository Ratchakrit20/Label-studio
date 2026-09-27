"""Label Studio ML backend: YOLO26-Seg pre-labels the COCO `person` class only."""

from __future__ import annotations

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from label_studio_sdk.converter.brush import mask2rle
from ultralytics import YOLO
from ultralytics.utils.downloads import attempt_download_asset


class YOLO26PersonSegmentation(LabelStudioMLBase):
    FROM_NAME = "label"
    TO_NAME = "image"
    IMAGE_KEY = "image"
    PERSON_CLASS_ID = 0  # COCO class 0
    PERSON_LABEL = "person"
    DEFAULT_DOCUMENT_ROOT = Path(__file__).resolve().parents[2]
    DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "yolo26s-seg.pt"

    def setup(self) -> None:
        model_path = Path(os.getenv("YOLO_MODEL_PATH", str(self.DEFAULT_MODEL_PATH))).expanduser().resolve()
        if not model_path.is_file():
            model_path.parent.mkdir(parents=True, exist_ok=True)
            attempt_download_asset(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(f"Unable to download YOLO checkpoint: {model_path}")
        self.confidence = float(os.getenv("YOLO_CONF", "0.25"))
        self.image_size = int(os.getenv("YOLO_IMGSZ", "640"))
        self.device = os.getenv("YOLO_DEVICE") or None
        self.model = YOLO(str(model_path))
        self.set("model_version", f"yolo26-person-seg:{model_path.name}")

    @staticmethod
    def _document_root() -> Path:
        value = os.getenv("LOCAL_FILES_DOCUMENT_ROOT")
        root = Path(value) if value else YOLO26PersonSegmentation.DEFAULT_DOCUMENT_ROOT
        root = root.expanduser().resolve()
        if not root.is_dir():
            raise RuntimeError(f"Local-files document root does not exist: {root}")
        return root

    def _resolve_image_path(self, task: Dict) -> Path:
        image_ref = task.get("data", {}).get(self.IMAGE_KEY)
        if not image_ref:
            raise ValueError(f"Task {task.get('id')} has no data['{self.IMAGE_KEY}']")

        # Check native Windows paths before urlparse(), which interprets "C:" as a URL scheme.
        native_path = Path(image_ref)
        parsed = urlparse(image_ref)
        if native_path.is_absolute():
            candidate = native_path.resolve()
        elif parsed.path.endswith("/data/local-files/"):
            values = parse_qs(parsed.query).get("d")
            if not values:
                raise ValueError(f"Local-files URL has no d parameter: {image_ref}")
            candidate = (self._document_root() / unquote(values[0])).resolve()
        elif parsed.scheme == "file":
            candidate = Path(unquote(parsed.path.lstrip("/"))).resolve()
        else:
            raise ValueError(
                "This backend expects Label Studio Local Files. "
                f"Unsupported image reference: {image_ref}"
            )

        root = self._document_root()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Image is outside LOCAL_FILES_DOCUMENT_ROOT: {candidate}") from exc
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    def predict(
        self,
        tasks: List[Dict],
        context: Optional[Dict] = None,
        **kwargs,
    ) -> ModelResponse:
        predictions = []

        for task in tasks:
            image_path = self._resolve_image_path(task)
            inference_args = {
                "source": str(image_path),
                "classes": [self.PERSON_CLASS_ID],
                "conf": self.confidence,
                "imgsz": self.image_size,
                # Return masks in the original image dimensions instead of
                # upscaling a low-resolution prototype mask afterwards.
                "retina_masks": True,
                "verbose": False,
            }
            if self.device:
                inference_args["device"] = self.device

            output = self.model.predict(**inference_args)[0]
            regions = []

            if output.masks is not None and output.boxes is not None:
                masks = output.masks.data.detach().cpu().numpy()
                scores = output.boxes.conf.detach().cpu().tolist()
                class_ids = output.boxes.cls.detach().cpu().tolist()

                for raw_mask, score, class_id in zip(masks, scores, class_ids):
                    if int(class_id) != self.PERSON_CLASS_ID:
                        continue
                    width, height = int(output.orig_shape[1]), int(output.orig_shape[0])
                    binary = (raw_mask > 0.5).astype(np.uint8)
                    mask = cv2.resize(binary, (width, height), interpolation=cv2.INTER_NEAREST) * 255
                    regions.append(
                        {
                            "id": uuid4().hex[:10],
                            "from_name": self.FROM_NAME,
                            "to_name": self.TO_NAME,
                            "type": "brushlabels",
                            "score": float(score),
                            "original_width": int(output.orig_shape[1]),
                            "original_height": int(output.orig_shape[0]),
                            "image_rotation": 0,
                            "value": {"format": "rle", "rle": mask2rle(mask), "brushlabels": [self.PERSON_LABEL]},
                        }
                    )

            mean_score = (
                sum(region["score"] for region in regions) / len(regions)
                if regions
                else 0.0
            )
            predictions.append(
                {
                    "result": regions,
                    "score": mean_score,
                    "model_version": self.model_version,
                }
            )

        return ModelResponse(predictions=predictions)

    def fit(self, event, data, **kwargs):
        """This backend is prediction-only; it never trains on manual PPE labels."""
        return {"status": "prediction-only", "event": event}
