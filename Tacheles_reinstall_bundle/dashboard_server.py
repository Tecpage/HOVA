#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import datetime
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from typing import Optional, Any, Dict, Tuple

import yaml


STATUS_EDIT_ALLOWED = ["Keyed", "In Bearbeitung", "Freigemeldet", "Formal abgenommen"]
BEARBEITER_EDIT_ALLOWED = ["HOCHTIEF", "Apleona", "WISAG", "pwrd", "Köster", "Andere"]

DATE_FIELDS = {
    "datum_anzeige",
    "termin_mangelbeseitigung",
    "nachfrist_2",
    "nachfrist_3",
    "termin_freimeldung",
    "mangel_abgestellt_am",
    "bestaetigung_am",
}

MAZ_FIELD = "nr_ht"


def now_ts() -> str:
    # DD.MM.YYYY HH:MM:SS
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def fingerprint_from_file(yaml_path: str) -> str:
    try:
        ts = os.path.getmtime(yaml_path)
    except Exception:
        ts = datetime.datetime.now().timestamp()
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%Y%m%d-%H%M%S")


def parse_date_any(value: Any) -> Optional[datetime.date]:
    s = str(value or "").strip()
    if not s:
        return None

    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m_iso:
        y, mo, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        return datetime.date(y, mo, d)

    m_dmy = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", s)
    if m_dmy:
        d, mo, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        return datetime.date(y, mo, d)

    raise ValueError("Ungültiges Datum: %s" % s)


def format_dmy(d: Optional[datetime.date]) -> Optional[str]:
    if d is None:
        return None
    return d.strftime("%d.%m.%Y")


def normalize_maz(value: Any) -> Optional[str]:
    s = str(value or "").strip()
    if not s:
        return None
    m = re.search(r"(\d{1,3})", s)
    if not m:
        return s
    num = int(m.group(1))
    return "MAZ %03d" % num


def get_nested(d: Dict[str, Any], path: str) -> Any:
    cur = d
    for p in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def set_nested(d: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def atomic_write_text(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def validate_deadlines(defect: Dict[str, Any]) -> None:
    # Rules:
    # - Nachfrist 2 > Frist
    # - Nachfrist 3 > Nachfrist 2 (if set) else > Frist
    # - Freimeldung > last(Frist, Nachfrist 2, Nachfrist 3)
    fr = parse_date_any(defect.get("termin_mangelbeseitigung")) if defect.get("termin_mangelbeseitigung") else None
    n2 = parse_date_any(defect.get("nachfrist_2")) if defect.get("nachfrist_2") else None
    n3 = parse_date_any(defect.get("nachfrist_3")) if defect.get("nachfrist_3") else None
    fm = parse_date_any(defect.get("termin_freimeldung")) if defect.get("termin_freimeldung") else None

    if n2 and not fr:
        raise ValueError("Nachfrist 2 benötigt zuerst eine Frist.")
    if n2 and fr and not (n2 > fr):
        raise ValueError("Nachfrist 2 muss nach der Frist liegen.")

    if n3 and not fr:
        raise ValueError("Nachfrist 3 benötigt zuerst eine Frist.")
    if n3 and n2 and not (n3 > n2):
        raise ValueError("Nachfrist 3 muss nach Nachfrist 2 liegen.")
    if n3 and fr and not n2 and not (n3 > fr):
        raise ValueError("Nachfrist 3 muss nach der Frist liegen.")

    if fm:
        last = None
        for d in (fr, n2, n3):
            if d is None:
                continue
            if last is None or d > last:
                last = d
        if last is None:
            raise ValueError("Freimeldung benötigt mindestens eine Frist.")
        if not (fm > last):
            raise ValueError("Freimeldung muss nach der letzten Frist liegen.")


class App(object):
    def __init__(self, root_dir: str):
        self.root = os.path.abspath(root_dir)
        self.yaml_path = os.path.join(self.root, "Tacheles.yaml")
        self.versions_dir = os.path.join(self.root, ".versions")

        if not os.path.isfile(self.yaml_path):
            raise FileNotFoundError("Tacheles.yaml nicht gefunden: %s" % self.yaml_path)

    def load_doc(self) -> Dict[str, Any]:
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        if "defects" not in doc or not isinstance(doc.get("defects"), list):
            doc["defects"] = []
        if "change_log" not in doc or not isinstance(doc.get("change_log"), list):
            doc["change_log"] = []
        if "meta" not in doc or not isinstance(doc.get("meta"), dict):
            doc["meta"] = {}
        return doc

    def dump_doc(self, doc: Dict[str, Any]) -> str:
        return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)

    def write_doc_with_version(self, yaml_text: str) -> None:
        # atomic write main yaml
        atomic_write_text(self.yaml_path, yaml_text)

        # write a version snapshot (hidden folder)
        ensure_dir(self.versions_dir)
        base = datetime.datetime.now().strftime("Tacheles_%Y%m%d_%H%M%S")
        snap = os.path.join(self.versions_dir, base + ".yaml")
        i = 1
        while os.path.exists(snap):
            snap = os.path.join(self.versions_dir, "%s_%d.yaml" % (base, i))
            i += 1
        with open(snap, "w", encoding="utf-8") as f:
            f.write(yaml_text)

    def find_defect(self, doc: Dict[str, Any], defect_id: str) -> Optional[Dict[str, Any]]:
        for d in doc.get("defects", []):
            if str(d.get("id")) == str(defect_id):
                return d
        return None

    def apply_update(self, defect: Dict[str, Any], field: str, value: Any) -> Tuple[bool, Any, Any]:
        old = get_nested(defect, field) if "." in field else defect.get(field)
        new = value

        # normalization & validation
        if field == MAZ_FIELD:
            new = normalize_maz(value)

        if field in DATE_FIELDS:
            if str(value or "").strip() == "":
                new = None
            else:
                d = parse_date_any(value)
                new = format_dmy(d)

        if field == "status":
            if str(value or "").strip() == "":
                raise ValueError("Status ist ein Pflichtfeld.")
            if value not in STATUS_EDIT_ALLOWED:
                raise ValueError("Ungültiger Status. Erlaubt: %s" % ", ".join(STATUS_EDIT_ALLOWED))
            new = value

        if field == "zustaendigkeit":
            if str(value or "").strip() == "":
                raise ValueError("Aktueller Bearbeiter ist ein Pflichtfeld.")
            if value not in BEARBEITER_EDIT_ALLOWED:
                raise ValueError("Ungültiger Bearbeiter. Erlaubt: %s" % ", ".join(BEARBEITER_EDIT_ALLOWED))
            new = value

        if field == "acceptance.wisag_formal_acceptance":
            v = str(value or "").strip().lower()
            if v in ("accepted", "open", "na", ""):
                new = v if v else None
            else:
                raise ValueError("Ungültiger Wert für WISAG-Abnahme (accepted/open/na).")

        # apply
        if "." in field:
            set_nested(defect, field, new)
        else:
            defect[field] = new

        changed = (old != new)
        return changed, old, new

    def update_defect(self, defect_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        doc = self.load_doc()
        defect = self.find_defect(doc, defect_id)
        if defect is None:
            raise KeyError("Mangel nicht gefunden.")

        # Copy current defect for rollback (deep-ish)
        before = yaml.safe_load(yaml.safe_dump(defect, sort_keys=False, allow_unicode=True))

        changed_any = False
        changes = []

        for field, value in patch.items():
            if field == "id":
                raise ValueError("Feld 'id' darf nicht geändert werden.")
            changed, old, new = self.apply_update(defect, field, value)
            if changed:
                changed_any = True
                changes.append((field, old, new))

        # deadline validation after patch
        try:
            validate_deadlines(defect)
        except Exception:
            defect.clear()
            defect.update(before)
            raise

        if not changed_any:
            return {"defect": defect, "changed": False}

        ts = now_ts()
        for field, old, new in changes:
            doc["change_log"].append({
                "ts": ts,
                "id": defect_id,
                "field": field,
                "old": old,
                "new": new,
            })

        doc["meta"]["last_modified"] = ts

        yaml_text = self.dump_doc(doc)
        self.write_doc_with_version(yaml_text)

        return {"defect": defect, "changed": True}

    def append_remark(self, defect_id: str, field: str, ts: str, text: str) -> Dict[str, Any]:
        if field not in ("bearbeitungsstand",):
            raise ValueError("Append ist nur für 'bearbeitungsstand' freigegeben.")
        raw = str(text or "").strip()
        if not raw:
            raise ValueError("Text fehlt.")
        words = [w for w in re.split(r"\s+", raw) if w]
        if len(words) < 10:
            raise ValueError("Bemerkung benötigt mind. 10 Wörter.")

        ts_s = str(ts or "").strip()
        if not re.match(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}$", ts_s):
            ts_s = now_ts()

        entry = "[%s] %s" % (ts_s, raw)

        doc = self.load_doc()
        defect = self.find_defect(doc, defect_id)
        if defect is None:
            raise KeyError("Mangel nicht gefunden.")

        old_val = str(defect.get(field) or "").rstrip()
        new_val = (old_val + "\n" if old_val else "") + entry
        defect[field] = new_val

        doc["change_log"].append({
            "ts": now_ts(),
            "id": defect_id,
            "field": field,
            "old": old_val,
            "new": new_val,
            "append": True,
        })
        doc["meta"]["last_modified"] = now_ts()

        yaml_text = self.dump_doc(doc)
        self.write_doc_with_version(yaml_text)

        return {"defect": defect, "changed": True}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)

        if p.path.startswith("/api/"):
            return self.handle_api_get(p)

        # redirect root to dashboard
        if p.path == "/" or p.path == "":
            self.send_response(302)
            self.send_header("Location", "/dashboard/")
            self.end_headers()
            return

        # map /dashboard/ -> /dashboard/index.html
        if p.path == "/dashboard" or p.path == "/dashboard/":
            self.path = "/dashboard/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        p = urlparse(self.path)
        if p.path == "/api/update":
            return self.handle_api_update()
        if p.path == "/api/append_remark":
            return self.handle_api_append_remark()

        self.send_json({"ok": False, "error": "Not found"}, code=404)

    def end_headers(self):
        # hard disable caching (requested: no stale UI)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        SimpleHTTPRequestHandler.end_headers(self)

    def read_json_body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except Exception:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def send_json(self, obj: Dict[str, Any], code: int = 200) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_api_get(self, p) -> None:
        if p.path == "/api/health":
            return self.send_json({"ok": True})

        if p.path == "/api/data":
            try:
                doc = APP.load_doc()
                fp = fingerprint_from_file(APP.yaml_path)
                return self.send_json({
                    "ok": True,
                    "fingerprint": fp,
                    "count": len(doc.get("defects", [])),
                    "rows": doc.get("defects", []),
                })
            except Exception as e:
                return self.send_json({"ok": False, "error": str(e)}, code=500)

        return self.send_json({"ok": False, "error": "Not found"}, code=404)

    def handle_api_update(self) -> None:
        body = self.read_json_body()
        defect_id = str(body.get("id") or "").strip()
        if not defect_id:
            return self.send_json({"ok": False, "error": "id fehlt"}, code=400)

        patch = {}
        if isinstance(body.get("patch"), dict):
            patch = body.get("patch")
        else:
            field = str(body.get("field") or "").strip()
            if not field:
                return self.send_json({"ok": False, "error": "field fehlt"}, code=400)
            patch[field] = body.get("value")

        try:
            res = APP.update_defect(defect_id, patch)
            fp = fingerprint_from_file(APP.yaml_path)
            return self.send_json({"ok": True, "fingerprint": fp, "row": res["defect"]})
        except KeyError as e:
            return self.send_json({"ok": False, "error": str(e)}, code=404)
        except Exception as e:
            return self.send_json({"ok": False, "error": str(e)}, code=400)

    def handle_api_append_remark(self) -> None:
        body = self.read_json_body()
        defect_id = str(body.get("id") or "").strip()
        field = str(body.get("field") or "").strip()
        ts = str(body.get("ts") or "").strip()
        text = str(body.get("text") or "")

        if not defect_id:
            return self.send_json({"ok": False, "error": "id fehlt"}, code=400)
        if not field:
            return self.send_json({"ok": False, "error": "field fehlt"}, code=400)

        try:
            res = APP.append_remark(defect_id, field, ts, text)
            fp = fingerprint_from_file(APP.yaml_path)
            return self.send_json({"ok": True, "fingerprint": fp, "row": res["defect"]})
        except KeyError as e:
            return self.send_json({"ok": False, "error": str(e)}, code=404)
        except Exception as e:
            return self.send_json({"ok": False, "error": str(e)}, code=400)


def main():
    if len(sys.argv) < 3:
        print("Usage: dashboard_server.py <port> <root_dir>")
        sys.exit(1)

    port = int(sys.argv[1])
    root_dir = sys.argv[2]

    global APP
    APP = App(root_dir)

    handler = partial(Handler, directory=root_dir)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)

    print("Tacheles Dashboard läuft auf http://127.0.0.1:%d/dashboard/" % port)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
