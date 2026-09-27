"""Import a Label Studio JSON export into an existing project by image filename.

Usage:
  conda activate label-studio
  python labeling/import_json.py "D:\\path\\export.json" Savety

Project may be Savety, Splitter, Cable-sagging, or a numeric project ID.
Existing images/tasks are reused. Exact duplicate annotations are skipped.
Only result types that match the current project schema are imported.
"""
import argparse
import json
import os
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "labeling" / "runtime" / "label-studio-fresh"
DB = DATA_DIR / "label_studio.sqlite3"


def image_name(value):
    parsed = urlparse(str(value or ""))
    raw = parse_qs(parsed.query).get("d", [parsed.path])[0]
    return Path(unquote(raw).replace("\\", "/")).name.casefold()


def controls(xml):
    result = {}
    for node in ET.fromstring(xml).iter():
        if node.tag.endswith("Labels") and node.get("name"):
            result[node.get("name")] = (
                node.tag.lower(),
                {label.get("value") for label in node.findall("Label")},
            )
        elif node.tag == "TextArea" and node.get("name"):
            result[node.get("name")] = ("textarea", set())
    return result


def normalize_result(result, schema):
    accepted, skipped = [], 0
    for region in result or []:
        target = schema.get(region.get("from_name"))
        if not target:
            skipped += 1
            continue
        expected, allowed = target
        if region.get("type") != expected:
            skipped += 1
            continue
        labels = region.get("value", {}).get(region["type"], [])
        if allowed and not set(labels).issubset(allowed):
            skipped += 1
            continue
        accepted.append(region)
    return accepted, skipped


def fingerprint(result):
    return json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser(description="Import annotations into existing Label Studio image tasks")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("project", help="Savety, Splitter, Cable-sagging, or project ID")
    parser.add_argument("--dry-run", action="store_true", help="Check matching/conversion without writing")
    args = parser.parse_args()
    source_path = args.json_file.expanduser().resolve()
    payload = json.loads(source_path.read_text(encoding="utf-8-sig"))
    source_tasks = payload.get("tasks", []) if isinstance(payload, dict) else payload
    if not isinstance(source_tasks, list):
        raise SystemExit("JSON must be a Label Studio task list or an object containing tasks")

    os.environ.update(
        LABEL_STUDIO_BASE_DATA_DIR=str(DATA_DIR),
        LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=str(ROOT),
        LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED="true",
        LOCAL_FILES_DOCUMENT_ROOT=str(ROOT),
        LATEST_VERSION_CHECK="false",
        ML_BLOCK_LOCAL_IP="false",
    )
    from label_studio.server import _setup_env
    _setup_env()
    from django.contrib.auth import get_user_model
    from projects.models import Project
    from rest_framework.test import APIClient
    from tasks.models import Task

    project = Project.objects.get(id=int(args.project)) if args.project.isdigit() else Project.objects.get(title__iexact=args.project)
    schema = controls(project.label_config)
    existing = {}
    for task in Task.objects.filter(project=project).prefetch_related("annotations"):
        key = image_name(task.data.get("image"))
        if key in existing:
            raise SystemExit(f"Duplicate image filename in project: {key}")
        existing[key] = task

    matched = added = duplicates = missing = skipped_regions = 0
    prepared = []
    for source_task in source_tasks:
        task = existing.get(image_name(source_task.get("data", {}).get("image", source_task.get("image_value"))))
        if task is None:
            missing += 1
            continue
        matched += 1
        known = {fingerprint(a.result) for a in task.annotations.all()}
        for annotation in source_task.get("annotations", []):
            result, skipped = normalize_result(annotation.get("result", []), schema)
            skipped_regions += skipped
            if not result:
                continue
            mark = fingerprint(result)
            if mark in known:
                duplicates += 1
                continue
            known.add(mark)
            prepared.append((task.id, annotation, result))

    if not args.dry_run and prepared:
        backup = DATA_DIR / "before-import-json.sqlite3"
        with sqlite3.connect(DB) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)
        client = APIClient()
        client.force_authenticate(user=get_user_model().objects.first())
        for task_id, annotation, result in prepared:
            body = {"result": result}
            for key in ("was_cancelled", "ground_truth", "lead_time"):
                if key in annotation:
                    body[key] = annotation[key]
            response = client.post(f"/api/tasks/{task_id}/annotations/", body, format="json", HTTP_HOST="localhost")
            if response.status_code >= 300:
                raise RuntimeError(f"task {task_id}: HTTP {response.status_code}: {response.data}")
            added += 1

    print(json.dumps({
        "project": project.title,
        "source_tasks": len(source_tasks),
        "matched_tasks": matched,
        "missing_tasks": missing,
        "new_annotations": len(prepared) if args.dry_run else added,
        "duplicate_annotations": duplicates,
        "skipped_regions": skipped_regions,
        "dry_run": args.dry_run,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
