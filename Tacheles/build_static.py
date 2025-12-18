#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tacheles – Static Export

Purpose:
- Exports Tacheles.yaml into a JSON file that the dashboard frontend can load
  when no /api/* backend is available (static hosting / GitLab Pages).

Output:
- dashboard/data.json  (same directory as index.html / app.js / styles.css)

This keeps the online deployment minimalist:
- read-only reporting for viewers
- edits happen via Git (YAML) and are then redeployed by CI
"""

import os
import json
import datetime
import yaml  # type: ignore


def fingerprint_from_file(path: str) -> str:
    try:
        ts = os.path.getmtime(path)
    except Exception:
        ts = datetime.datetime.now().timestamp()
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%Y%m%d-%H%M%S")


def main() -> None:
    root = os.path.abspath(os.path.dirname(__file__))
    yaml_path = os.path.join(root, "Tacheles.yaml")
    dash_dir = os.path.join(root, "dashboard")
    out_path = os.path.join(dash_dir, "data.json")

    with open(yaml_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}

    rows = doc.get("defects", [])
    if not isinstance(rows, list):
        rows = []

    payload = {
        "ok": True,
        "fingerprint": fingerprint_from_file(yaml_path),
        "count": len(rows),
        "rows": rows,
    }

    os.makedirs(dash_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("[OK] wrote", out_path)


if __name__ == "__main__":
    main()
