#!/usr/bin/env python3
import os, sys, json, subprocess, signal, time, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
ROOT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path.cwd().resolve()
CFG  = ROOT / "apps.yaml"
DASH = ROOT / "dashboard"
STATE_FILE = ROOT / ".launcher_state.json"

STATE_LOCK = threading.Lock()
STATE = {"started": {}}  # id -> {"pid": int, "ts": float, "cmd": list, "cwd": str}

def now_ts(): return time.time()

def load_cfg():
    if yaml is None:
        raise RuntimeError("PyYAML fehlt. Installiere: python3 -m pip install --user pyyaml")
    if not CFG.exists():
        raise FileNotFoundError(f"apps.yaml nicht gefunden: {CFG}")
    data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    apps = data.get("apps", [])
    if not isinstance(apps, list):
        apps = []
    # normalize
    out = []
    for a in apps:
        if not isinstance(a, dict): 
            continue
        if not a.get("id") or not a.get("name") or not a.get("workdir") or not a.get("script"):
            continue
        # Expand ~/ and $VARS to make the config portable
        workdir = os.path.expanduser(os.path.expandvars(str(a["workdir"])))
        script  = str(a["script"])
        out.append({
            "id": str(a["id"]),
            "name": str(a["name"]),
            "workdir": workdir,
            "script": script,
            "args": [str(x) for x in (a.get("args") or [])],
        })
    return out

def write_state():
    with STATE_LOCK:
        STATE_FILE.write_text(json.dumps(STATE, ensure_ascii=False, indent=2), encoding="utf-8")

def cleanup_dead():
    with STATE_LOCK:
        dead = []
        for app_id, meta in STATE["started"].items():
            pid = meta.get("pid")
            if not pid:
                dead.append(app_id)
                continue
            try:
                os.kill(pid, 0)
            except Exception:
                dead.append(app_id)
        for d in dead:
            STATE["started"].pop(d, None)
    write_state()

def start_app(app_id: str):
    apps = load_cfg()
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app:
        raise ValueError(f"Unknown app id: {app_id}")

    cleanup_dead()

    with STATE_LOCK:
        if app_id in STATE["started"]:
            return STATE["started"][app_id]

    cwd = app["workdir"]
    cmd = [app["script"], *app["args"]]

    # best-effort chmod
    try:
        subprocess.run(["chmod", "+x", app["script"]], cwd=cwd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # Start detached (no new Terminal windows). We inherit no stdout/stderr.
    p = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    meta = {"pid": p.pid, "ts": now_ts(), "cmd": cmd, "cwd": cwd}
    with STATE_LOCK:
        STATE["started"][app_id] = meta
    write_state()
    return meta

def stop_app(app_id: str):
    cleanup_dead()
    with STATE_LOCK:
        meta = STATE["started"].get(app_id)
    if not meta:
        return {"stopped": False, "reason": "not_running"}

    pid = meta["pid"]
    # terminate process group
    try:
        os.killpg(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    time.sleep(0.2)
    cleanup_dead()
    return {"stopped": True}

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Avoid stale assets; makes "Hard Reload" unnecessary
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/launcher/"):
            rel = path[len("/launcher/"):] or "index.html"
            return str((DASH / rel).resolve())
        if path == "/":
            return str((DASH / "index.html").resolve())
        return super().translate_path(path)

    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/launcher"):
            self.send_response(302)
            self.send_header("Location", "/launcher/")
            self.end_headers()
            return
        if p == "/api/health":
            self._json({"ok": True, "root": str(ROOT)})
            return
        if p == "/api/apps":
            try:
                apps = load_cfg()
            except Exception as e:
                self._json({"error": str(e)}, status=500)
                return
            cleanup_dead()
            with STATE_LOCK:
                started = STATE["started"].copy()
            self._json({"apps": apps, "started": started})
            return
        if p == "/api/stop_all":
            cleanup_dead()
            with STATE_LOCK:
                ids = list(STATE["started"].keys())
            results = {}
            for i in ids:
                results[i] = stop_app(i)
            self._json({"ok": True, "results": results})
            return
        return super().do_GET()

    def do_POST(self):
        p = urlparse(self.path).path
        length = int(self.headers.get("Content-Length","0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {}

        if p == "/api/run":
            app_id = str(payload.get("id") or "")
            try:
                meta = start_app(app_id)
                self._json({"ok": True, "meta": meta})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=400)
            return

        if p == "/api/stop":
            app_id = str(payload.get("id") or "")
            try:
                res = stop_app(app_id)
                self._json({"ok": True, "result": res})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=400)
            return

        self.send_response(404)
        self.end_headers()

def main():
    DASH.mkdir(parents=True, exist_ok=True)
    if yaml is None:
        # allow UI to show error
        pass
    if not STATE_FILE.exists():
        write_state()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Launcher running: http://127.0.0.1:{PORT}/launcher/")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
