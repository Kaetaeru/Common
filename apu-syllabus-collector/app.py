from __future__ import annotations

import json
import socket
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from strict_manager import CollectionManager

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
MANAGER = CollectionManager(ROOT)


class Handler(BaseHTTPRequestHandler):
    server_version = "APUSyllabusCollector/1.6"
    def log_message(self, format, *args): print("[collector]", format % args)
    def send_json(self, payload, status=200):
        body=json.dumps(payload, ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def send_file(self, path: Path, content_type: str):
        if not path.exists(): self.send_error(HTTPStatus.NOT_FOUND); return
        body=path.read_bytes(); self.send_response(200); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def read_json(self):
        length=int(self.headers.get("Content-Length","0"));
        if length<0 or length>1_000_000: raise ValueError("Request body too large.")
        return json.loads((self.rfile.read(length) if length else b"{}").decode())
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=="/": self.send_file(WEB_DIR/"index.html","text/html; charset=utf-8"); return
        if parsed.path=="/app.css": self.send_file(WEB_DIR/"app.css","text/css; charset=utf-8"); return
        if parsed.path=="/app.js": self.send_file(WEB_DIR/"app.js","application/javascript; charset=utf-8"); return
        if parsed.path=="/api/status": self.send_json(MANAGER.status(parse_qs(parsed.query).get("college",[MANAGER.college])[0])); return
        self.send_error(HTTPStatus.NOT_FOUND)
    def do_POST(self):
        parsed=urlparse(self.path)
        try:
            payload=self.read_json(); college=str(payload.get("college") or MANAGER.college or "APM").upper()
            if parsed.path=="/api/load-data":
                data=MANAGER.ensure_dataset(college, refresh=bool(payload.get("refresh",False))); self.send_json({"ok":True,"term":data["term"],"classes":len(data["classes"]),"status":MANAGER.status(college)}); return
            if parsed.path=="/api/start": MANAGER.start(college=college, headless=bool(payload.get("headless",False)), worker_count=payload.get("workerCount")); self.send_json({"ok":True}); return
            if parsed.path=="/api/retry-failed": MANAGER.start(college=college, headless=bool(payload.get("headless",False)), retry_failed_only=True, worker_count=payload.get("workerCount")); self.send_json({"ok":True}); return
            if parsed.path=="/api/pause": MANAGER.pause(); self.send_json({"ok":True}); return
            if parsed.path=="/api/resume": MANAGER.resume(); self.send_json({"ok":True}); return
            if parsed.path=="/api/stop": MANAGER.stop(); self.send_json({"ok":True}); return
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc: self.send_json({"ok":False,"error":str(exc)},400)


def free_port():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock: sock.bind(("127.0.0.1",0)); return int(sock.getsockname()[1])


def main():
    try: port=8766; server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    except OSError: port=free_port(); server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    url=f"http://127.0.0.1:{port}/"; print(f"APU Syllabus Collector running at {url}"); print(f"Output: {ROOT/'data/syllabus_links.json'}"); threading.Timer(.7,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: MANAGER.stop()
    finally: server.server_close()

if __name__=="__main__": main()
