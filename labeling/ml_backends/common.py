"""Shared utilities for local-file Label Studio ML backends."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, unquote, urlparse


def document_root(default_root: Path) -> Path:
    """Return and validate the root allowed for Label Studio local files."""
    root = Path(os.getenv("LOCAL_FILES_DOCUMENT_ROOT", str(default_root))).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(f"LOCAL_FILES_DOCUMENT_ROOT does not exist: {root}")
    return root


def resolve_local_image(task: Dict[str, Any], image_key: str, default_root: Path) -> Path:
    """Resolve a Label Studio local-files URL safely to an image on disk."""
    image_ref = task.get("data", {}).get(image_key) or task.get("data", {}).get("$undefined$")
    if not image_ref:
        raise ValueError(f"Task {task.get('id')} has no image in data['{image_key}']")

    parsed = urlparse(str(image_ref))
    native_path = Path(str(image_ref))
    if native_path.is_absolute():
        candidate = native_path.resolve()
    elif parsed.path.endswith("/data/local-files/"):
        values = parse_qs(parsed.query).get("d")
        if not values:
            raise ValueError(f"Local-files URL has no d parameter: {image_ref}")
        candidate = (document_root(default_root) / unquote(values[0])).resolve()
    elif parsed.scheme == "file":
        candidate = Path(unquote(parsed.path.lstrip("/"))).resolve()
    else:
        raise ValueError(f"Unsupported image reference: {image_ref}")

    root = document_root(default_root)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Image is outside LOCAL_FILES_DOCUMENT_ROOT: {candidate}") from exc
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def yolo_box_result(*, region_id: str, from_name: str, to_name: str, label: str,
                    score: float, x1: float, y1: float, x2: float, y2: float,
                    width: int, height: int) -> Dict[str, Any]:
    """Convert an absolute-pixel YOLO box to a Label Studio rectangle result."""
    return {
        "id": region_id,
        "from_name": from_name,
        "to_name": to_name,
        "type": "rectanglelabels",
        "score": float(score),
        "original_width": width,
        "original_height": height,
        "image_rotation": 0,
        "value": {
            "x": max(0.0, min(100.0, x1 / width * 100)),
            "y": max(0.0, min(100.0, y1 / height * 100)),
            "width": max(0.0, min(100.0, (x2 - x1) / width * 100)),
            "height": max(0.0, min(100.0, (y2 - y1) / height * 100)),
            "rotation": 0,
            "rectanglelabels": [label],
        },
    }
