"""Send one existing Label Studio task directly to an ML backend (read-only)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "labeling" / "runtime" / "label-studio-fresh" / "label_studio.sqlite3"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test one task against a Label Studio ML backend")
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:9094")
    args = parser.parse_args()

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute("SELECT id, data FROM task WHERE id = ?", (args.task_id,)).fetchone()
    if row is None:
        raise SystemExit(f"Task {args.task_id} was not found in {DATABASE}")

    task = {"id": row[0], "data": json.loads(row[1])}
    response = requests.post(f"{args.url.rstrip('/')}/predict", json={"tasks": [task]}, timeout=120)
    response.raise_for_status()
    payload = response.json()
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    # Current label-studio-ml returns ``results``; older backends used
    # ``predictions``. Support both response shapes in this diagnostic tool.
    predictions = payload.get("results", payload.get("predictions", []))
    result_count = len(predictions[0].get("result", [])) if predictions else 0
    print(f"\nDetected regions: {result_count}")


if __name__ == "__main__":
    main()
