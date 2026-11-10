# Label Studio — เริ่มงาน Safety และ Splitter

## เริ่มงานแต่ละวัน (เปิดคนละ PowerShell terminal)

เริ่มทุก terminal ที่ `D:\ratchakt\Label-studio` และปล่อย terminal ของบริการที่ใช้เปิดค้างไว้ (`Ctrl+C` เพื่อหยุด) ไม่ต้องติดตั้งแพ็กเกจหรือรัน `connect_models.py` ทุกวัน

**Terminal 1 — Label Studio (ต้องเปิดเสมอ)**

```powershell
cd D:\ratchakt\Label-studio
conda activate label-studio
$env:LABEL_STUDIO_BASE_DATA_DIR = "$PWD\labeling\runtime\label-studio-fresh"
$env:LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED = "true"
$env:LOCAL_FILES_SERVING_ENABLED = "true"
$env:LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:LATEST_VERSION_CHECK = "false"
$env:ML_BLOCK_LOCAL_IP = "false"
label-studio start --no-browser --internal-host 127.0.0.1 --port 8080 --data-dir $env:LABEL_STUDIO_BASE_DATA_DIR
```

**Terminal 2 — เลือกอย่างใดอย่างหนึ่งตามโปรเจกต์ที่ทำ**

Safety (`Savety`): person mask + lat-long/datetime ที่พอร์ต `9090`

```powershell
cd D:\ratchakt\Label-studio
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:YOLO_MODEL_PATH = "$PWD\Savety\label_studio_yolo26_person\models\yolo26s-seg.pt"
$env:METADATA_MODEL_PATH = "$PWD\lat-long\models\best.pt"
$env:YOLO_CONF = "0.25"
$env:YOLO_IMGSZ = "640"
$env:YOLO_CONFIG_DIR = "$PWD\Savety\label_studio_yolo26_person\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\Savety\label_studio_yolo26_person\runtime\label-studio-ml"
python .\Savety\label_studio_yolo26_person\_wsgi.py --host 127.0.0.1 --port 9090
```

Splitter: SP + Good/NotGood/NotApplicable + ODF + lat-long/datetime ที่พอร์ต `9097`

```powershell
cd D:\ratchakt\Label-studio
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:YOLO_CONF = "0.25"
$env:YOLO_IMGSZ = "640"
$env:YOLO_CONFIG_DIR = "$PWD\labeling\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\labeling\runtime\splitter-combined"
python .\labeling\ml_backends\splitter_combined\_wsgi.py --host 127.0.0.1 --port 9097
```

ถ้า ODF detector ไม่พบ `cabinet` ระบบจะเสนอ `NotApplicable` แทน Good/NotGood. ก่อนเปิดโค้ดใหม่นี้ ให้เพิ่ม `<Choice value="NotApplicable"/>` ใน **Splitter → Settings → Labeling Interface** แล้ว Save; การแก้ไฟล์ XML ใน workspace ไม่เปลี่ยน config ของโปรเจกต์ในฐานข้อมูล. ตรวจแก้ผลด้วยมือหาก detector พลาด `cabinet`.

**Terminal 3 — SAM (เฉพาะเมื่อใช้ Smart point/box)**

```powershell
cd D:\ratchakt\Label-studio
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:YOLO_CONFIG_DIR = "$PWD\labeling\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\labeling\runtime\sam"
$env:SAM_MODEL_PATH = "$PWD\labeling\models\sam2.1_t.pt"
python .\labeling\sam_backend.py
```

เข้า `http://127.0.0.1:8080` แล้วเลือกโปรเจกต์ ตรวจว่า Safety เชื่อม `9090` หรือ Splitter เชื่อม `9097` ใน Settings → Model. หากมีการเชื่อมอยู่แล้ว ไม่ต้องเพิ่มซ้ำ. เลือกหนึ่งรูปแล้วใช้ Actions → Retrieve Predictions เพื่อทดสอบ; terminal ของโมเดลที่เลือกควรมี `POST /predict`. หากต้องการให้แสดง prediction ตอนเปิดรูป ให้เลือกโมเดลเดียวกันใน Settings → Annotation → Prelabeling แล้ว Save.

คำสั่งพอร์ต `9092`–`9094` และ `9096` ด้านล่างเป็นตัวทดลองแยกโมเดล ไม่ใช่คำสั่งเริ่มงานประจำ

ชุดนี้มี 3 โปรเจกต์: `Savety`, `Splitter` และ `Cable-sagging`

- Label Studio: `http://127.0.0.1:8080`
- YOLO person: `http://127.0.0.1:9090` ตรวจคนอัตโนมัติใน Savety
- SAM: `http://127.0.0.1:9091` ทำงานเฉพาะเมื่อใช้ Smart point/box

YOLO และ SAM เป็นคนละ backend ไม่มีการใช้ webhook เพื่อ inference และการ Submit annotation ไม่ได้ train โมเดล

## ไฟล์ที่ใช้งาน

| ไฟล์ | หน้าที่ |
|---|---|
| `sam_backend.py` | SAM interactive backend พอร์ต 9091 |
| `connect_models.py` | กู้การเชื่อมโมเดลเมื่อข้อมูลการเชื่อมหาย ไม่ใช้ทุกวัน |
| `import_json.py` | นำเข้า annotation JSON จากอีกเครื่องและจับคู่รูปเดิม |
| `requirements-label-studio.txt` | ไลบรารี conda `label-studio` |
| `requirements-ai.txt` | ไลบรารี conda `yolo26_FTTR` |
| `models/sam2.1_t.pt` | น้ำหนัก SAM 2.1 Tiny; ดาวน์โหลดอัตโนมัติถ้าไม่มี |
| `runtime/label-studio-fresh/` | ฐานข้อมูล Label Studio ที่ใช้งานจริง |
| `../Savety/label_studio_yolo26_person/model.py` | ตรวจ `person` และกรอบ `lat-long`/`datetime` |
| `../Savety/label_studio_yolo26_person/_wsgi.py` | เปิด YOLO backend พอร์ต 9090 |
| `../Savety/label_studio_yolo26_person/models/yolo26s-seg.pt` | น้ำหนัก YOLO segmentation; ดาวน์โหลดอัตโนมัติถ้าไม่มี |

## ติดตั้งบนเครื่องใหม่

ติดตั้ง Anaconda หรือ Miniconda และ Git แล้วเปิด Anaconda PowerShell Prompt ที่ราก Dataset

### Label Studio environment

```powershell
conda create -n label-studio python=3.12 pip -y
conda activate label-studio
python -m pip install --upgrade pip
python -m pip install -r .\labeling\requirements-label-studio.txt
```

### AI environment สำหรับ NVIDIA CUDA 12.1

```powershell
conda create -n yolo26_FTTR python=3.11 pip git -y
conda activate yolo26_FTTR
python -m pip install --upgrade pip
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r .\labeling\requirements-ai.txt
python -m pip check
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```


คัดลอกโฟลเดอร์รูป, checkpoint `.pt` ที่ฝึกเอง และ `labeling/runtime/label-studio-fresh/` จากเครื่องเดิมโดยรักษาโครงสร้างเดิม ฐานข้อมูลมี task, annotation และบัญชีผู้ใช้ จึงควรส่งผ่านช่องทางส่วนตัว

## เปิดใช้งาน

ใช้คำสั่งในหัวข้อ **เริ่มงานแต่ละวัน** ด้านบน: เปิด Label Studio `8080` และ backend ของโปรเจกต์ที่ทำ (`9090` สำหรับ Savety หรือ `9097` สำหรับ Splitter). เปิด SAM `9091` เพิ่มเฉพาะเมื่อใช้ Smart point/box. ไม่ต้องเปิด backend เดี่ยว `9092`–`9094` หรือรุ่นทดลอง `9096`.

ทดสอบบริการที่เปิดด้วย `Invoke-RestMethod http://127.0.0.1:PORT/health` แล้วเลือกหนึ่งรูปใน Data Manager → Actions → Retrieve Predictions → OK. Terminal ของโมเดลต้องแสดง `POST /predict`.

### เปิด ML แยกทีละตัว (สำหรับทดสอบหรือโปรเจกต์แยก)

เปิด Label Studio `8080` ตาม Terminal 1 ก่อน แล้วเลือก **หนึ่งคำสั่งด้านล่างใน PowerShell terminal ใหม่**. แต่ละ backend จะเปิดค้างเพื่อรอรูป; หยุดด้วย `Ctrl+C`. หากจะใช้ในโปรเจกต์เดียวกับ combined backend ให้ตรวจรายการใน Settings → Model ก่อน เพราะการเชื่อมหลาย backend อาจทำให้ Retrieve Predictions เรียกตัวที่ไม่ต้องการ.

**SP / FTTH — `detector`, พอร์ต `9092`**

```powershell
cd D:\ratchakt\Label-studio
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:YOLO_MODEL_PATH = "$PWD\Splitter\models\ftth\best.pt"
$env:YOLO_CONF = "0.25"
$env:YOLO_IMGSZ = "640"
$env:YOLO_CONFIG_DIR = "$PWD\labeling\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\labeling\runtime\detector-ftth"
python .\labeling\ml_backends\detector\_wsgi.py --host 127.0.0.1 --port 9092
```

ผลเป็นกรอบ SP; ใช้ `Splitter/ftth_label_config.xml` สำหรับโปรเจกต์ FTTH แยก. URL ที่เชื่อมคือ `http://127.0.0.1:9092`.

**Good/NotGood + ODF — `fttr_odf`, พอร์ต `9093`**

```powershell
cd D:\ratchakt\Label-studio
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:CLASSIFICATION_MODEL_PATH = "$PWD\Splitter\models\fttr\classification_baseline.pt"
$env:DETECTION_MODEL_PATH = "$PWD\Splitter\models\fttr\detection_yolo26s_7class_640v1_production.pt"
$env:YOLO_CONF = "0.25"
$env:YOLO_IMGSZ = "640"
$env:YOLO_CONFIG_DIR = "$PWD\labeling\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\labeling\runtime\fttr-odf"
python .\labeling\ml_backends\fttr_odf\_wsgi.py --host 127.0.0.1 --port 9093
```

ผลเป็น `Choices name="quality"` และกรอบ `object`; ใช้ `Splitter/fttr_label_config.xml` สำหรับโปรเจกต์ FTTR แยก. URL คือ `http://127.0.0.1:9093`.

**lat-long/datetime — `metadata_ocr`, พอร์ต `9094`**

ชื่อโฟลเดอร์เป็นชื่อเดิม; backend นี้ตรวจกรอบเท่านั้น **ไม่มี OCR อ่านข้อความ**. ตั้ง `LS_FROM_NAME` ให้ตรงกับ Labeling Interface ของโปรเจกต์.

```powershell
cd D:\ratchakt\Label-studio
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:METADATA_MODEL_PATH = "$PWD\lat-long\models\best.pt"
$env:METADATA_CONF = "0.25"
$env:METADATA_IMGSZ = "640"
$env:LS_FROM_NAME = "object" # Splitter/โปรเจกต์ lat-long; Safety ใช้ metadata_box
$env:YOLO_CONFIG_DIR = "$PWD\labeling\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\labeling\runtime\metadata-detector"
python .\labeling\ml_backends\metadata_ocr\_wsgi.py --host 127.0.0.1 --port 9094
```

URL คือ `http://127.0.0.1:9094`. สำหรับ Safety ให้เปลี่ยน `LS_FROM_NAME` เป็น `metadata_box` **ก่อนเปิด process** แต่การทำงานประจำของ Safety ใช้ combined `9090` อยู่แล้ว.


## เชื่อมโมเดลกลับเข้าโปรเจกต์

เมื่อย้ายฐานข้อมูลหรือการเชื่อมโมเดลหาย ให้เปิด backend ก่อนแล้วรัน:

```powershell
conda activate label-studio
python .\labeling\connect_models.py
```

สคริปต์ปัจจุบันตั้ง Safety เป็น backend รวม `9090` และ Splitter เป็น backend รวม `9097`; รันเฉพาะเมื่อการเชื่อมในฐานข้อมูลหาย และต้องเปิด backend ที่สคริปต์ตรวจสถานะก่อน ไม่ใช้เป็นคำสั่งเริ่มงานประจำ

## นำเข้า JSON จากอีกเครื่อง

โปรเจกต์ปลายทางต้องมี task รูปเดิมอยู่แล้ว ระบบจับคู่ด้วยชื่อไฟล์ ข้าม annotation ซ้ำ และไม่แปลง Polygon

ตรวจโดยยังไม่เขียนฐานข้อมูล:

```powershell
conda activate label-studio
python .\labeling\import_json.py "D:\งาน\export.json" Savety --dry-run
```

นำเข้าจริง:

```powershell
python .\labeling\import_json.py "D:\ratchakt\Label-studio\labeling\label-json\savety\project-1-at-2026-09-27-21-34-611016fc.json" Savety
python .\labeling\import_json.py "D:\ratchakt\Label-studio\labeling\label-json\splitter\project-2-at-2026-09-27-21-34-3810a61e.json" Splitter
python .\labeling\import_json.py "D:\ratchakt\Label-studio\labeling\label-json\cable-sagging\project-3-at-2026-09-27-21-34-c6341cbd.json" Cable-sagging
```

ใช้ชื่อ `Savety`, `Splitter`, `Cable-sagging` หรือ project ID ได้ ก่อนเขียนจริงระบบสำรองฐานข้อมูลล่าสุดไว้ที่ `labeling/runtime/label-studio-fresh/before-import-json.sqlite3` ผลลัพธ์ที่ชนิดไม่ตรง schema รวมถึง Polygon จะถูกข้ามและนับใน `skipped_regions`

## ก่อนอัปโหลด Git

ไม่ควร commit ข้อมูลต่อไปนี้ลง public repository:

```text
Image_Sorted/
Image_Sorted.zip
Cable-sagging/images_fixed/
labeling/runtime/
label-studio-backups/
**/cache.db
**/__pycache__/
```

ไฟล์ `.pt` ถูกตัดออกด้วย `.gitignore` โมเดลที่ฝึกเองต้องคัดลอกแยกจาก Git; เฉพาะโมเดลสาธารณะที่โค้ดรองรับจึงอาจดาวน์โหลดอัตโนมัติ

การดาวน์โหลดครั้งแรกต้องเชื่อมต่ออินเทอร์เน็ต และอาจใช้เวลาตามความเร็วเครือข่าย ห้าม commit `Image_Sorted.zip` เพราะมีขนาดประมาณ 5.4 GB



cd D:\ratchakt\Label-studio
conda activate label-studio

$env:LABEL_STUDIO_BASE_DATA_DIR = "$PWD\labeling\runtime\label-studio-fresh"

New-Item -ItemType Directory -Force .\exports

label-studio export 1 JSON --export-path="$PWD\exports\Savety.json"
label-studio export 2 JSON --export-path="$PWD\exports\Splitter.json"
label-studio export 3 JSON --export-path="$PWD\exports\Cable-sagging.json"
