# FTTH / SP detection model

`best.pt` is a YOLO detection model with these classes: `pole`, `SP2_Correct`, `SP2_Incorrect_Unclear`, `SP_Open`, `SP_Close`, `SP_Damaged`, `nameplate`, `Fast_Connector`, `Connector_Correct`, and `Connector_Wrong_Type`.

Create a dedicated Label Studio project with `../../ftth_label_config.xml`. Start the generic detector on port 9092 and connect `http://127.0.0.1:9092`. This model is inference-only; reviewed annotations do not retrain it automatically.
