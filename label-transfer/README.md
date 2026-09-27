# ย้าย Label Studio annotations ไปอีกเครื่อง

เครื่องมือนี้จับคู่ Task ด้วย **ชื่อไฟล์รูป** แล้วเพิ่มเฉพาะ annotations ลงใน Task ที่มีอยู่แล้ว
โปรแกรมจะไม่อัปโหลดรูปและไม่สร้าง Task ใหม่

## โครงสร้าง

```text
label-transfer/
├── label_transfer.py
└── README.md

label-studio-backups/
└── exports/                 # เก็บไฟล์ JSON ที่ Export แล้ว
```

## สิ่งที่ต้องเตรียมบนเครื่องปลายทาง

1. ติดตั้งและเปิด Label Studio
2. สร้าง Project และนำรูปชุดเดิมเข้าไปก่อน
3. ควรใช้ Labeling Interface เดียวกับ Project ต้นทาง
4. ชื่อไฟล์รูปต้องตรงกัน และไม่ควรมีชื่อซ้ำใน Project
5. เตรียม Legacy Token ของเครื่องปลายทาง

## วิธีแนะนำ: Export ผ่านหน้าเว็บ

ที่เครื่องต้นทาง เปิด Project → **Export** → เลือก **JSON** แล้วนำไฟล์ JSON ไปเครื่องปลายทาง

บนเครื่องปลายทาง เปิด PowerShell ในโฟลเดอร์นี้แล้วรัน:

```powershell
python label_transfer.py import --project-id 1 --file "D:\path\export.json"
```

เปลี่ยน `1` เป็น Project ID ปลายทาง โปรแกรมจะถาม Legacy Token โดยไม่แสดง token บนหน้าจอ

## Export ผ่าน command line

ถ้าต้องการสำรองด้วยสคริปต์:

```powershell
python label_transfer.py export --project-id 1 --file "..\label-studio-backups\exports\project-1.json"
```

สคริปต์ดาวน์โหลด Project JSON ครั้งเดียว จึงเร็วกว่าวิธีเดิมที่อ่านทีละ Task

## ระบุเซิร์ฟเวอร์หรือ token ผ่าน environment

```powershell
$env:LABEL_STUDIO_TOKEN="LEGACY_TOKEN"
python label_transfer.py import --server "http://127.0.0.1:8080" --project-id 1 --file "D:\path\export.json"
```

## อ่านผลลัพธ์

- `Imported annotations` จำนวน annotation ที่เพิ่มสำเร็จ
- `Skipped duplicates` มี annotation เดิมอยู่แล้ว จึงไม่เพิ่มซ้ำ
- `Unmatched images` ไม่พบชื่อไฟล์รูปใน Project ปลายทาง
- `Ambiguous filenames` พบชื่อไฟล์ซ้ำหลาย Task จึงข้ามเพื่อป้องกันลง Label ผิดรูป

สามารถรัน import ซ้ำได้ เพราะสคริปต์ตรวจและข้าม annotation ที่เหมือนเดิม

