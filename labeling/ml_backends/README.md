# Local ML backends

Each backend is a separate HTTP process. Label Studio calls its `/predict` endpoint; models are loaded once on startup, not on every image.

| Backend | Port | Model | Output |
|---|---:|---|---|
| `metadata_ocr` | 9091 | `lat-long/models/best.pt` | `lat-long`/`datetime` boxes plus OCR text |
| `detector` (FTTH) | 9092 | `Splitter/models/ftth/best.pt` | 10 FTTH/SP boxes |
| `fttr_odf` | 9093 | FTTR classifier + 7-class detector | `Good`/`NotGood` plus ODF boxes |

All services require `LOCAL_FILES_DOCUMENT_ROOT` to point to the repository root. Run the commands in `labeling/README.md` from that root. Verify a service before connecting it:

```powershell
Invoke-RestMethod http://127.0.0.1:9091/health
```

Use the matching labeling config when creating each new project: `lat-long/label_config.xml`, `Splitter/ftth_label_config.xml`, or `Splitter/fttr_label_config.xml`. Names in a labeling config must exactly match the model class names.
