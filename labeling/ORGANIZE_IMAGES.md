# วิธีใช้ `organize_images.py`

สคริปต์นี้คัดลอกรูป `.jpg`, `.jpeg`, และ `.png` จากหลายโฟลเดอร์ แล้วแยกลงหมวดตามเลขท้ายของชื่อไฟล์ เช่น `photo_1.jpg` ถึง `photo_3.jpg` จะเข้าหมวดที่ 1 และทำต่อเนื่องถึงเลข `30` รูปต้นฉบับจะไม่ถูกย้ายหรือลบ

## 1. ตั้งค่า path ในโค้ด

เปิด `organize_images.py` แล้วแก้ส่วนบนสุดนี้:

```python
DEFAULT_SOURCES = [
    Path(r"D:\\ratchakt\\2026-10-01\\2026-10-01\\images_batch0004_20261006_042857"),
    # Path(r"D:\\โฟลเดอร์รูปอีกชุด"),
]
DEFAULT_DESTINATION = Path(r"D:\\ratchakt\\Label-studio\\Image_Sorted")
```

เพิ่ม source ได้อีกบรรทัดละหนึ่ง `Path(...)` และเปลี่ยน `DEFAULT_DESTINATION` เป็นที่เก็บรูปที่ต้องการได้เลย `r` ข้างหน้าข้อความ path ต้องคงไว้

## 2. รันด้วย path ที่ตั้งในโค้ด

เปิด PowerShell ในโฟลเดอร์โปรเจกต์ แล้วใช้ environment Python ที่ติดตั้งไว้:

```powershell
conda activate label-studio
python .\labeling\organize_images.py
```

สคริปต์นี้ใช้เฉพาะ Python standard library จึงไม่ต้องติดตั้งแพ็กเกจเพิ่มใน environment `label-studio`

## 3. ระบุ path จาก PowerShell

คำสั่งนี้จะใช้ path ที่พิมพ์ในคำสั่งแทน `DEFAULT_SOURCES` และ `DEFAULT_DESTINATION`:

```powershell
conda activate label-studio
python .\labeling\organize_images.py `
  --source "D:\ratchakt\2026-10-01\2026-10-01\images_batch0004_20261006_042857" `
  --source "D:\รูปงาน\batch-2" `
  --destination "D:\ratchakt\Label-studio\Image_Sorted"
```

เพิ่ม `--source "path"` ได้ไม่จำกัดจำนวน โฟลเดอร์ปลายทางจะถูกสร้างให้อัตโนมัติหากยังไม่มี

## 4. ทดลองก่อนคัดลอก

เติม `--dry-run` เพื่อดูจำนวนรูปที่จะคัดลอก โดยไม่สร้างไฟล์หรือแก้ไขอะไร:

```powershell
python .\labeling\organize_images.py --dry-run
```

หรือใช้ร่วมกับ path ที่ระบุเอง:

```powershell
python .\labeling\organize_images.py --source "D:\รูปงาน\batch-2" --destination "D:\รูปที่แยกแล้ว" --dry-run
```

## ข้อควรรู้

- สคริปต์อ่านเฉพาะไฟล์ที่อยู่ตรงในแต่ละ source ไม่อ่านโฟลเดอร์ย่อย
- ถ้าชื่อไฟล์ซ้ำกับไฟล์ในปลายทาง จะข้ามไฟล์นั้น เพื่อไม่เขียนทับรูปเดิม
- รูปที่ไม่มีเลขท้ายชื่อไฟล์ หรือเลขอยู่นอกช่วง 1–30 จะไปที่ `99_ตรวจสอบเลขท้ายไม่ตรงกติกา`
- หลังรันสำเร็จ สคริปต์จะสร้างหรืออัปเดต `README.md` ในโฟลเดอร์ปลายทาง พร้อมสรุปจำนวนรูป
