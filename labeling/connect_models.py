import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['ML_BLOCK_LOCAL_IP']='false'
os.environ.update(LABEL_STUDIO_BASE_DATA_DIR=str(ROOT/'labeling/runtime/label-studio-fresh'),LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=str(ROOT),LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED='true',LATEST_VERSION_CHECK='false')
from label_studio.server import _setup_env
_setup_env()
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from ml.models import MLBackend
client=APIClient()
client.force_authenticate(user=get_user_model().objects.first())
projects=json.loads((ROOT/'labeling/projects.json').read_text())
for job,p in projects.items():
    # Label Studio 1.23.1 uses the first backend as the automatic prediction
    # backend when a task is opened. Keep YOLO first for Savety; SAM remains a
    # separate interactive backend and is only used for smart point/box calls.
    models=[]
    if job=='Savety':
        models.append(('YOLO26 person','http://127.0.0.1:9090',False))
    models.append(('SAM 2.1 interactive','http://127.0.0.1:9091',True))
    for name,url,interactive in models:
        backend=MLBackend.objects.filter(project_id=p['id'],url=url).first()
        if backend is None:
            # Prediction-only backends do not need annotation/training webhooks.
            # 1.23.1 unconditionally creates a localhost-blocked webhook on normal save.
            # Bulk insert avoids that optional post_save integration, retaining SSRF protections.
            backend=MLBackend(project_id=p['id'],url=url,title=name,is_interactive=interactive)
            MLBackend.objects.bulk_create([backend])
            backend=MLBackend.objects.get(project_id=p['id'],url=url)
        # Keep the roles correct even when a backend connection already
        # existed.  Label Studio routes Smart point/box calls to an
        # interactive backend, so YOLO must never retain this flag.
        MLBackend.objects.filter(pk=backend.pk).update(title=name,is_interactive=interactive)
        backend.update_state()
        backend.refresh_from_db()
        if backend.state!='CO':
            raise RuntimeError(f'{job} {name}: {backend.state} {backend.error_message}')
        print(job,name,backend.state,flush=True)
