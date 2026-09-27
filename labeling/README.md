# Label Studio + YOLO person + SAM

ชุดนี้มี 3 โปรเจกต์: `Savety`, `Splitter` และ `Cable-sagging`

- Label Studio: `http://127.0.0.1:8080`
- YOLO person: `http://127.0.0.1:9090` ตรวจคนอัตโนมัติใน Savety
- SAM: `http://127.0.0.1:9091` ทำงานเฉพาะเมื่อใช้ Smart point/box

YOLO และ SAM เป็นคนละ backend ไม่มีการใช้ webhook เพื่อ inference และการ Submit annotation ไม่ได้ train โมเดล

## ไฟล์ที่ใช้งาน

| ไฟล์ | หน้าที่ |
|---|---|
| `sam_backend.py` | SAM interactive backend พอร์ต 9091 |
| `connect_models.py` | เชื่อม YOLO ก่อน SAM และกำหนด automatic/interactive |
| `import_json.py` | นำเข้า annotation JSON จากอีกเครื่องและจับคู่รูปเดิม |
| `requirements-label-studio.txt` | ไลบรารี conda `label-studio` |
| `requirements-ai.txt` | ไลบรารี conda `yolo26_FTTR` |
| `models/sam2.1_t.pt` | น้ำหนัก SAM 2.1 Tiny; ดาวน์โหลดอัตโนมัติถ้าไม่มี |
| `runtime/label-studio-fresh/` | ฐานข้อมูล Label Studio ที่ใช้งานจริง |
| `../Savety/label_studio_yolo26_person/model.py` | ตรวจ `person` และคืน Brush RLE |
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

คัดลอกโฟลเดอร์รูปและ `labeling/runtime/label-studio-fresh/` จากเครื่องเดิมโดยรักษาโครงสร้างเดิม ฐานข้อมูลมี task, annotation และบัญชีผู้ใช้ จึงควรส่งผ่านช่องทางส่วนตัว ไฟล์โมเดล `.pt` ไม่ต้องคัดลอกและไม่เก็บใน Git เพราะ backend จะดาวน์โหลดอัตโนมัติในการใช้งานครั้งแรก

## เปิดใช้งาน

เปิด PowerShell แยกแต่ละ Terminal โดยเริ่มจากราก Dataset

### Terminal 1 — Label Studio

```powershell
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

### Terminal 2 — YOLO person

```powershell
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:LOCAL_FILES_DOCUMENT_ROOT = "$PWD"
$env:YOLO_MODEL_PATH = "$PWD\Savety\label_studio_yolo26_person\models\yolo26s-seg.pt"
$env:YOLO_CONF = "0.25"
$env:YOLO_IMGSZ = "640"
$env:YOLO_CONFIG_DIR = "$PWD\Savety\label_studio_yolo26_person\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\Savety\label_studio_yolo26_person\runtime\label-studio-ml"
python .\Savety\label_studio_yolo26_person\_wsgi.py --host 127.0.0.1 --port 9090
```

`YOLO_IMGSZ=1024` ให้ขอบ mask ละเอียดกว่า `640` แต่ใช้ GPU และเวลามากขึ้น โค้ดเปิด `retina_masks` เพื่อบันทึก mask ตามขนาดภาพต้นฉบับ

### Terminal 3 — SAM (เปิดเฉพาะวันที่ต้องใช้)

```powershell
conda activate yolo26_FTTR
$env:PYTHONIOENCODING = "utf-8"
$env:YOLO_CONFIG_DIR = "$PWD\labeling\runtime\ultralytics"
$env:MODEL_DIR = "$PWD\labeling\runtime\sam"
$env:SAM_MODEL_PATH = "$PWD\labeling\models\sam2.1_t.pt"
python .\labeling\sam_backend.py
```

ไม่เปิด SAM ก็ยังใช้ Label Studio และ YOLO person ได้ เพียง Smart point/box ใช้งานไม่ได้ หยุดแต่ละบริการด้วย `Ctrl+C`

ตรวจบริการ:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod http://127.0.0.1:9090/health
Invoke-RestMethod http://127.0.0.1:9091/health
```

## เชื่อมโมเดลกลับเข้าโปรเจกต์

เมื่อย้ายฐานข้อมูลหรือการเชื่อมโมเดลหาย ให้เปิด backend ก่อนแล้วรัน:

```powershell
conda activate label-studio
python .\labeling\connect_models.py
```

Savety ต้องมีลำดับ `YOLO26 person` (`interactive=false`) ก่อน `SAM 2.1 interactive` (`interactive=true`)

## นำเข้า JSON จากอีกเครื่อง

โปรเจกต์ปลายทางต้องมี task รูปเดิมอยู่แล้ว ระบบจับคู่ด้วยชื่อไฟล์ ข้าม annotation ซ้ำ และไม่แปลง Polygon

ตรวจโดยยังไม่เขียนฐานข้อมูล:

```powershell
conda activate label-studio
python .\labeling\import_json.py "D:\งาน\export.json" Savety --dry-run
```

นำเข้าจริง:

```powershell
python .\labeling\import_json.py "D:\งาน\export.json" Savety
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

ไฟล์ `.pt` ถูกตัดออกด้วย `.gitignore` เมื่อเปิด YOLO หรือเรียก SAM ครั้งแรก ระบบจะดาวน์โหลดและวางไฟล์ไว้ที่ตำแหน่งที่ถูกต้องโดยอัตโนมัติ จึงไม่ต้องใช้ Git LFS

การดาวน์โหลดครั้งแรกต้องเชื่อมต่ออินเทอร์เน็ต และอาจใช้เวลาตามความเร็วเครือข่าย ห้าม commit `Image_Sorted.zip` เพราะมีขนาดประมาณ 5.4 GB
