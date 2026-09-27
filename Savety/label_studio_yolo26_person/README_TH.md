# YOLO26 person backend

คู่มือเริ่มงานปัจจุบันอยู่ที่ [Savety README](../README.md)

ใช้ conda `yolo26_FTTR`, โมเดล `models/yolo26s-seg.pt`, port 9090
ผลคือ `from_name=label`, `to_name=image`, `brushlabels=[person]` และ mask RLE ตรงกับ XML ใหม่
Document root เป็น Dataset (หาอัตโนมัติจากตำแหน่งสคริปต์) ใช้เฉพาะรูปภายในรากนี้
`start_backend.cmd` เปิดเฉพาะ YOLO; ใช้ `../START.cmd` เพื่อเปิดครบ Label Studio + YOLO + SAM
YOLO_CONF=0.25, YOLO_IMGSZ=640; ตั้ง YOLO_DEVICE=cpu หากไม่ใช้ GPU
ไม่มีการ train หรือแก้น้ำหนักเมื่อ Submit annotation
