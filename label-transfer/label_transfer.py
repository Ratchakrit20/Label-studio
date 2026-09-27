#!/usr/bin/env python
"""Transfer Label Studio annotations without creating tasks or images."""

import argparse
import getpass
import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


_bearer_tokens = {}
_refresh_lock = threading.Lock()


def refresh_personal_token(server, token):
    url = server.rstrip("/") + "/api/token/refresh"
    payload = json.dumps({"refresh": token}).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        result = json.loads(response.read())
    access_token = result.get("access")
    if not access_token:
        raise RuntimeError("Personal Access Token refresh returned no access token")
    _bearer_tokens[(server, token)] = access_token
    return access_token


def api_request(server, token, method, path, body=None, allow_refresh=True):
    url = server.rstrip("/") + path
    data = None
    bearer = _bearer_tokens.get((server, token))
    headers = {
        "Authorization": f"Bearer {bearer}" if bearer else f"Token {token}"
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=120) as response:
            payload = response.read()
            return json.loads(payload) if payload else None
    except HTTPError as error:
        if error.code == 401 and allow_refresh:
            try:
                # Only one worker refreshes an expired PAT access token.
                with _refresh_lock:
                    current = _bearer_tokens.get((server, token))
                    if not bearer or current == bearer:
                        refresh_personal_token(server, token)
                return api_request(
                    server, token, method, path, body, allow_refresh=False
                )
            except (HTTPError, URLError, RuntimeError, ValueError):
                pass
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} {url}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Connect failed {url}: {error.reason}") from error


def image_value(task):
    return str((task.get("data") or {}).get("image") or "")


def filename_key(value):
    if not value:
        return ""
    path = urlsplit(value).path
    leaf = unquote(path.replace("\\", "/").rsplit("/", 1)[-1])
    # Uploaded files often have a hash/UUID prefix added by Label Studio.
    leaf = re.sub(r"^[0-9a-fA-F-]{32,}-", "", leaf)
    leaf = re.sub(r"^[0-9a-fA-F]{8,}-", "", leaf)
    return leaf.casefold()


def get_project_export(server, token, project_id):
    """Download all project tasks in one request (much faster than task-by-task)."""
    response = api_request(
        server,
        token,
        "GET",
        f"/api/projects/{project_id}/export?exportType=JSON",
    )
    if not isinstance(response, list):
        raise RuntimeError("Project JSON export did not return a task list")
    return response


def fingerprint(result):
    return json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def export_labels(args, token):
    project = api_request(
        args.server, token, "GET", f"/api/projects/{args.project_id}/"
    )
    records = []

    print("Downloading project JSON export...")
    for task in get_project_export(args.server, token, args.project_id):
        annotations = []
        for annotation in task.get("annotations") or []:
            annotations.append(
                {
                    "result": annotation.get("result") or [],
                    "was_cancelled": bool(annotation.get("was_cancelled", False)),
                    "ground_truth": bool(annotation.get("ground_truth", False)),
                    "lead_time": annotation.get("lead_time"),
                }
            )
        if not annotations:
            continue

        value = image_value(task)
        records.append(
            {
                "source_task_id": task["id"],
                "image_value": value,
                "file_name_key": filename_key(value),
                "annotations": annotations,
            }
        )

    backup = {
        "format_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_server": args.server,
        "source_project": args.project_id,
        "project_title": project.get("title"),
        "label_config": project.get("label_config"),
        "tasks": records,
    }
    args.file.write_text(
        json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Exported {len(records)} labeled task(s): {args.file.resolve()}")


def add_lookup(lookup, key, task):
    if key:
        lookup.setdefault(key, []).append(task)


def import_labels(args, token):
    backup = json.loads(args.file.read_text(encoding="utf-8-sig"))
    print("Reading target project in one request...")
    target_tasks = get_project_export(args.server, token, args.project_id)
    exact_lookup = {}
    name_lookup = {}

    for task in target_tasks:
        value = image_value(task)
        add_lookup(exact_lookup, value, task)
        add_lookup(name_lookup, filename_key(value), task)

    created = duplicates = unmatched = ambiguous = 0

    # Accept both this script's compact backup and Label Studio's normal JSON export.
    if isinstance(backup, list):
        source_records = []
        for task in backup:
            value = image_value(task)
            source_records.append(
                {
                    "image_value": value,
                    "file_name_key": filename_key(value),
                    "annotations": task.get("annotations") or [],
                }
            )
    else:
        source_records = backup.get("tasks", [])

    for record in source_records:
        matches = exact_lookup.get(record.get("image_value"), [])
        if not matches:
            matches = name_lookup.get(record.get("file_name_key"), [])

        if not matches:
            unmatched += 1
            print(f"WARNING: no existing image: {record.get('file_name_key')}")
            continue
        if len(matches) != 1:
            ambiguous += 1
            print(f"WARNING: duplicate filename: {record.get('file_name_key')}")
            continue

        task_id = int(matches[0]["id"])
        existing = {
            fingerprint(annotation.get("result") or [])
            for annotation in (matches[0].get("annotations") or [])
        }

        for annotation in record.get("annotations", []):
            result = annotation.get("result") or []
            result_fingerprint = fingerprint(result)
            if result_fingerprint in existing:
                duplicates += 1
                continue

            body = {
                "result": result,
                "was_cancelled": bool(annotation.get("was_cancelled", False)),
                "ground_truth": bool(annotation.get("ground_truth", False)),
                "lead_time": annotation.get("lead_time"),
                "task": task_id,
            }
            api_request(
                args.server,
                token,
                "POST",
                f"/api/tasks/{task_id}/annotations/",
                body,
            )
            existing.add(result_fingerprint)
            created += 1

    print(f"Imported annotations : {created}")
    print(f"Skipped duplicates   : {duplicates}")
    print(f"Unmatched images     : {unmatched}")
    print(f"Ambiguous filenames  : {ambiguous}")
    print("No images or tasks were created.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Move Label Studio annotations without copying images."
    )
    parser.add_argument("mode", choices=("export", "import"))
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument(
        "--file", type=Path, default=None, help="Backup JSON input/output file"
    )
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    parser.add_argument(
        "--token",
        default=os.environ.get("LABEL_STUDIO_TOKEN", ""),
        help="Legacy Token; omit to enter it securely",
    )
    args = parser.parse_args()
    if args.file is None:
        args.file = Path(f"labels-project-{args.project_id}.json")
    return args


def main():
    args = parse_args()
    token = args.token or getpass.getpass("Label Studio Legacy Token: ")
    if not token:
        raise RuntimeError("Token is required")
    if args.mode == "export":
        export_labels(args, token)
    else:
        if not args.file.is_file():
            raise FileNotFoundError(args.file)
        import_labels(args, token)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
