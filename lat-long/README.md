# Metadata detection

`models/best.pt` detects two regions: `lat-long` and `datetime`. โมเดลนี้เป็น object detector จึงคืนเฉพาะกรอบตำแหน่ง ไม่อ่านข้อความในภาพ.

Use `label_config.xml`. Start the backend on port 9094 as documented in `../labeling/README.md`, then connect `http://127.0.0.1:9094` in this project's **Settings → Model**.
