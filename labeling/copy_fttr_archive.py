"""Copy the seven-class FTTR archive into the eight-class FTTR dataset.

The source archive is read only. Class 2 (fiber_cable) is omitted; old class
IDs 3..6 become 2..5. The new classes spl3/spl3_open have no archive labels.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SOURCE = Path(r"E:\ratchakt\AI-Inspect-FTTR\training_archive\dataset_7class_balanced")
TARGET = Path(r"D:\ratchakt\AI-Train-Models\datasets\fttr")
CLASS_MAP = {0: 0, 1: 1, 3: 2, 4: 3, 5: 4, 6: 5}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Copy files; default is a dry run")
    args = parser.parse_args()

    plan = []
    existing_stems = {
        path.stem.casefold()
        for split in ("train", "val")
        for path in (TARGET / "images" / split).iterdir()
        if path.is_file()
    }
    for split in ("train", "val"):
        image_dir = SOURCE / "images" / split
        label_dir = SOURCE / "labels" / split
        for image in sorted(image_dir.iterdir()):
            if image.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            label = label_dir / f"{image.stem}.txt"
            if not label.is_file():
                raise ValueError(f"Missing label for {image}")
            if image.stem.casefold() in existing_stems:
                raise ValueError(f"Image stem already exists in target: {image.stem}")
            existing_stems.add(image.stem.casefold())
            converted = []
            for line_number, line in enumerate(label.read_text(encoding="utf-8").splitlines(), 1):
                fields = line.split()
                if not fields:
                    continue
                old_id = int(fields[0])
                if old_id == 2:
                    continue
                if old_id not in CLASS_MAP or len(fields) < 5:
                    raise ValueError(f"Invalid annotation {label}:{line_number}")
                converted.append(" ".join((str(CLASS_MAP[old_id]), *fields[1:])))
            if not converted:
                raise ValueError(f"No retained labels for {image}")
            destination_image = TARGET / "images" / split / image.name
            destination_label = TARGET / "labels" / split / label.name
            if destination_image.exists() or destination_label.exists():
                raise FileExistsError(f"Target already exists: {image.stem}")
            plan.append((image, destination_image, destination_label, converted))

    print(f"Validated {len(plan)} image/label pairs (train={sum(x[1].parent.name == 'train' for x in plan)}, "
          f"val={sum(x[1].parent.name == 'val' for x in plan)})")
    if not args.apply:
        print("Dry run only. Pass --apply to copy.")
        return
    for source_image, destination_image, destination_label, converted in plan:
        shutil.copy2(source_image, destination_image)
        destination_label.write_text("\n".join(converted) + "\n", encoding="utf-8")
    print(f"Copied {len(plan)} pairs; source archive unchanged")


if __name__ == "__main__":
    main()
