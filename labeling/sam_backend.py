"""Local SAM2 interactive backend: polygons for PPE, lossless RLE for cables."""
import os
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image
from ultralytics import SAM
from ultralytics.utils.downloads import attempt_download_asset
from label_studio_ml.api import init_app
from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from label_studio_sdk.converter.brush import mask2rle

ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()
MODEL = None

def local_image(task):
    ref = task['data']['image']
    url = urlparse(ref)
    if url.path != '/data/local-files/':
        raise ValueError('Only workspace local-files images are supported')
    path = (ROOT / parse_qs(url.query)['d'][0]).resolve()
    path.relative_to(ROOT)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path

class InteractiveSAM(LabelStudioMLBase):
    def setup(self):
        self.set('model_version', 'sam2.1-t-local-v1')

    def predict(self, tasks, context=None, **kwargs):
        global MODEL
        prompts = [r for r in (context or {}).get('result', []) if r.get('from_name') in {'sam_point', 'sam_box', 'cable_point', 'cable_box'} and r.get('type') in {'keypointlabels', 'rectanglelabels'}]
        if not prompts:
            # SAM is interactive-only. Never create stored predictions unless
            # Label Studio sends an explicit smart point or smart box prompt.
            return ModelResponse(predictions=[])
        if len(tasks) != 1:
            raise ValueError('Interactive SAM requires exactly one task')
        target_type = 'brushlabels'
        target = 'label' if prompts[-1]['from_name'].startswith('sam_') else 'cable'
        selected = prompts[-1]['value'][prompts[-1]['type']][0]
        cfg = self.parsed_label_config.get(target, {})
        if selected not in cfg.get('labels', []):
            raise ValueError('Prompt label is not present in target control')
        path = local_image(tasks[0])
        with Image.open(path) as im:
            width, height = im.size
        points, signs, box = [], [], None
        for r in prompts:
            v = r['value']
            if v.get(r['type'], [None])[0] != selected:
                continue
            x, y = v['x']*width/100, v['y']*height/100
            if r['type'] == 'keypointlabels':
                points.append([x, y])
                signs.append(int(r.get('is_positive', True)))
            else:
                box = [x, y, x+v['width']*width/100, y+v['height']*height/100]
        args = dict(source=str(path), verbose=False, device=os.getenv('SAM_DEVICE', '0'), retina_masks=True, conf=0.01)
        if points:
            args.update(points=points, labels=signs)
        if box:
            args['bboxes'] = [box]
        with LOCK:
            if MODEL is None:
                model_file = Path(os.getenv('SAM_MODEL_PATH', str(ROOT/'labeling/models/sam2.1_t.pt')))
                if not model_file.is_file():
                    model_file.parent.mkdir(parents=True, exist_ok=True)
                    attempt_download_asset(model_file)
                if not model_file.is_file():
                    raise FileNotFoundError(f'Unable to download SAM checkpoint: {model_file}')
                MODEL = SAM(str(model_file))
            output = MODEL.predict(**args)[0]
        regions = []
        if output.masks is not None:
            for raw in output.masks.data.cpu().numpy():
                mask = cv2.resize((raw > 0.5).astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST)
                common = dict(from_name=target, to_name='image', original_width=width, original_height=height, image_rotation=0, type=target_type)
                if target_type == 'brushlabels':
                    regions.append(dict(common, id=uuid4().hex[:10], value={'format': 'rle', 'rle': mask2rle(mask*255), 'brushlabels': [selected]}))
                else:
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for contour in contours:
                        if cv2.contourArea(contour) < 9:
                            continue
                        polygon = cv2.approxPolyDP(contour, 0.7, True).reshape(-1, 2)
                        if len(polygon) >= 3:
                            coords = [[min(100., max(0., float(x)*100/width)), min(100., max(0., float(y)*100/height))] for x,y in polygon]
                            regions.append(dict(common, id=uuid4().hex[:10], value={'points': coords, 'polygonlabels': [selected], 'closed': True}))
        return ModelResponse(predictions=[{'result': regions, 'model_version': self.model_version}])

    def fit(self, event, data, **kwargs):
        return {'status': 'prediction-only'}

if __name__ == '__main__':
    init_app(model_class=InteractiveSAM).run(host='127.0.0.1', port=9091, threaded=False)
