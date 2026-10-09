"""Copy images from one or more folders into numbered category folders."""

import argparse
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

FOLDERS = {
    1: "01_ก่อนและขณะปฏิบัติงาน_PPE",
    2: "02_Splitter_ก่อนติดตั้ง",
    3: "03_ค่าสัญญาณ_Splitter_ก่อนติดตั้ง",
    4: "04_Splitter_หลังติดตั้ง_Closure",
    5: "05_L3และSplitter_หลังติดตั้ง",
    6: "06_อุปกรณ์เสาไฟและสายก่อนเข้าบ้าน",
    7: "07_Clampและสายข้ามถนน",
    8: "08_เดินสายภายในบ้าน",
    9: "09_วัดค่าแสงและอุปกรณ์ลูกค้า",
    10: "10_ใบเสร็จ_BOQ_โปรโมชั่น",
}
REVIEW = "99_ตรวจสอบเลขท้ายไม่ตรงกติกา"
EXTENSIONS = {".jpeg", ".jpg", ".png"}

# แก้ไข path เริ่มต้นตรงนี้ได้เลย
# เพิ่มโฟลเดอร์รูปได้หลายบรรทัด โดยใส่ comma (,) คั่นในรายการ
DEFAULT_SOURCES = [
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0001_20261006_040851"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0002_20261006_041654"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0003_20261006_042255"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0004_20261006_042857"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0005_20261006_043431"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0006_20261006_044045"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0007_20261006_044612"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0008_20261006_045139"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0009_20261006_045651"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0010_20261006_050203"),
    Path(r"D:\ratchakt\2026-10-01\2026-10-01\images_batch0011_20261006_050652")
]
# โฟลเดอร์เก็บผลลัพธ์ สามารถเปลี่ยนเป็น path อื่นได้
DEFAULT_DESTINATION = Path(r"D:\ratchakt\Label-studio\All-image-LMR\2026-10-01")


def folder_for(path):
    match = re.search(r"_(\d+)$", path.stem)
    number = int(match.group(1)) if match else 0
    return FOLDERS[(number - 1) // 3 + 1] if 1 <= number <= 30 else REVIEW


def organize_images(sources, destination, dry_run=False):
    """Copy supported images from every source folder without overwriting names."""
    sources = [Path(source).resolve() for source in sources]
    destination = Path(destination).resolve()
    if not sources:
        raise ValueError("Provide at least one source folder.")
    for source in sources:
        if not source.is_dir():
            raise ValueError(f"Source folder does not exist: {source}")
        if source == destination or source in destination.parents or destination in source.parents:
            raise ValueError("Each source and destination must be separate, non-nested folders.")
    # Scan every output subfolder: a previously sorted filename is never copied again.
    existing = {p.name.casefold() for p in destination.rglob("*") if p.is_file()}
    stats = Counter()
    for source in sources:
        for path in sorted(source.iterdir()):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            stats["scanned"] += 1
            key = path.name.casefold()
            if key in existing:
                stats["skipped"] += 1
                continue
            folder = folder_for(path)
            target = destination / folder / path.name
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    # Exclusive creation prevents overwriting even if another run races us.
                    output = target.open("xb")
                except FileExistsError:
                    stats["skipped"] += 1
                    continue
                try:
                    with output, path.open("rb") as input_file:
                        shutil.copyfileobj(input_file, output)
                except BaseException:
                    target.unlink(missing_ok=True)
                    raise
            existing.add(key)
            stats["new"] += 1
            stats[folder] += 1
    if not dry_run:
        update_readme(sources, destination, stats)
    return stats


def update_readme(sources, destination, stats):
    """Recount actual images, including nested/unrecognized output folders."""
    counts = Counter()
    for path in destination.rglob("*"):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            relative = path.relative_to(destination)
            folder = relative.parts[0] if len(relative.parts) > 1 else "(โฟลเดอร์หลัก)"
            counts[folder] += 1
    ranges = {name: f"{topic * 3 - 2}–{topic * 3}" for topic, name in FOLDERS.items()}
    ranges[REVIEW] = "นอกช่วง 1–30 หรือไม่มีเลข"
    folders = list(ranges) + sorted(set(counts) - set(ranges))
    lines = [
        "# สรุปรูปภาพงานติดตั้ง", "",
        f"อัปเดตอัตโนมัติ: {datetime.now().astimezone().isoformat(timespec='seconds')}", "",
        "ยอดรวมด้านล่างนับจากไฟล์รูปที่มีอยู่จริงหลังรันสำเร็จ รวมโฟลเดอร์ย่อย ไม่ใช่เฉพาะรูปใหม่", "",
        "- โฟลเดอร์ต้นทาง:",
        *[f"  - `{source}`" for source in sources],
        f"- ปลายทาง: `{destination}`",
        f"- รูปต้นทางที่ตรวจรอบนี้: {stats['scanned']:,} รูป",
        f"- ข้ามชื่อไฟล์ที่มีแล้ว: {stats['skipped']:,} รูป",
        f"- คัดลอกใหม่รอบนี้: {stats['new']:,} รูป",
        f"- รูปทั้งหมดในปลายทาง: {sum(counts.values()):,} รูป", "",
        "| โฟลเดอร์ | เลขท้ายชื่อไฟล์ | เพิ่มรอบนี้ | รูปทั้งหมด |",
        "| --- | --- | ---: | ---: |",
    ]
    for folder in folders:
        label = folder.replace("|", "\\|")
        lines.append(f"| {label} | {ranges.get(folder, 'อื่น ๆ')} | {stats[folder]:,} | {counts[folder]:,} |")
    lines.extend([
        f"| **รวม** | | **{stats['new']:,}** | **{sum(counts.values()):,}** |", "",
        "## วิธีรัน", "",
        "แก้ `DEFAULT_SOURCES` และ `DEFAULT_DESTINATION` ด้านบนของ `organize_images.py` แล้วรัน:", "",
        "```powershell", "python organize_images.py", "```", "",
        "หรือระบุ path จาก PowerShell (ใส่ `--source` ซ้ำได้หลายครั้ง):", "",
        "```powershell", "python organize_images.py --source \"D:\\รูปชุดที่1\" --source \"D:\\รูปชุดที่2\" --destination \"D:\\รูปที่แยกแล้ว\"", "```", "",
        "ดูจำนวนโดยไม่คัดลอกหรือแก้ไข README:", "",
        "```powershell", "python organize_images.py --dry-run", "```", "",
        "## กติกา", "",
        "- รองรับ .jpeg, .jpg, .png และอ่านเลขหลัง _ ตัวสุดท้ายก่อนนามสกุล",
        "- อ่านไฟล์โดยตรงในทุกโฟลเดอร์ต้นทาง ไม่ค้นโฟลเดอร์ย่อยของต้นทาง",
        "- ข้ามชื่อไฟล์ที่มีอยู่ในปลายทางทุกโฟลเดอร์ย่อย โดยไม่แยกตัวพิมพ์ใหญ่–เล็ก",
        "- ตรวจซ้ำจากชื่อไฟล์ ไม่ใช่เนื้อหารูป: เปลี่ยนชื่อจะถือเป็นไฟล์ใหม่",
        "- ไม่เขียนทับรูปเดิม ไม่ย้ายหรือลบต้นฉบับ",
        "- หากลบรูปจากปลายทาง การรันใหม่จะคัดลอกกลับจากต้นทาง",
        "- README นี้สร้างใหม่หลังรันสำเร็จทุกครั้ง แม้ไม่มีรูปใหม่ อย่าใช้เก็บบันทึกส่วนตัว",
        "- ควรรันทีละครั้งและรอให้จบก่อนเริ่มรอบถัดไป", "",
    ])
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        action="append",
        help="Source image folder. Repeat --source for multiple folders.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_DESTINATION,
        help="Destination folder (default: DEFAULT_DESTINATION in this file).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without copying files")
    args = parser.parse_args()
    try:
        stats = organize_images(args.source or DEFAULT_SOURCES, args.destination, args.dry_run)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    print("DRY RUN - no files copied" if args.dry_run else "Copy complete")
    for key in ("scanned", "skipped", "new"):
        print(f"{key}: {stats[key]}")
    for folder in (*FOLDERS.values(), REVIEW):
        if stats[folder]:
            print(f"{folder}: {stats[folder]}")


if __name__ == "__main__":
    main()
