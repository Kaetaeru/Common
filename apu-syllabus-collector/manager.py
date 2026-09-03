from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from data_source import load_dataset
from mapping import load_mapping, save_mapping, valid_direct_url
from syllabus_sync import PORTAL_URL, _click_text, _make_driver, _page_links, _submit_search


class CollectionManager:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.output_file = self.root / "data" / "syllabus_links.json"
        self.state_file = self.root / "data" / "collector_state.json"
        self.log_file = self.root / "data" / "collector.log"
        self.lock = threading.RLock()
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event(); self.pause_event.set()
        self.running = False
        self.paused = False
        self.college = "APM"
        self.dataset: dict[str, Any] | None = None
        self.current: dict[str, Any] | None = None
        self.failed: dict[str, str] = {}
        self.logs: list[dict[str, str]] = []
        self.last_error = ""
        self._load_state()

    def _load_state(self) -> None:
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(raw, dict):
            self.college = str(raw.get("college") or "APM")
            failed = raw.get("failed")
            if isinstance(failed, dict): self.failed = {str(k): str(v) for k, v in failed.items()}

    def _save_state(self) -> None:
        payload = {"college": self.college, "failed": self.failed, "current": self.current, "updatedAt": time.time()}
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_file.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); temp.replace(self.state_file)

    def log(self, level: str, message: str) -> None:
        event = {"time": time.strftime("%H:%M:%S"), "level": level, "message": message}
        with self.lock:
            self.logs.append(event); self.logs = self.logs[-1000:]
        try:
            with self.log_file.open("a", encoding="utf-8") as handle: handle.write(f"[{event['time']}] {level.upper():5} {message}\n")
        except OSError: pass

    def ensure_dataset(self, college: str, refresh: bool = False) -> dict[str, Any]:
        self.log("info", f"Loading official timetable for {college.upper()}{' (refresh)' if refresh else ''}")
        data = load_dataset(self.root, college.upper(), refresh=refresh)
        with self.lock: self.college, self.dataset = college.upper(), data
        self._save_state(); self.log("ok", f"Loaded {data['term']} {self.college}: {len(data['classes'])} Class codes")
        return data

    def _cached_dataset(self, college: str) -> dict[str, Any] | None:
        if self.dataset and self.dataset.get("college") == college: return self.dataset
        path = self.root / "data" / f"classes_{college.lower()}.json"
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return None
        if isinstance(data, dict) and data.get("classes"): self.dataset = data; return data
        return None

    def start(self, *, college: str, headless: bool = False, refresh_data: bool = False, retry_failed_only: bool = False) -> None:
        with self.lock:
            if self.running: raise RuntimeError("Collector is already running.")
            self.running, self.paused, self.last_error = True, False, ""
            self.stop_event.clear(); self.pause_event.set()
        self.thread = threading.Thread(target=self._run, kwargs={"college": college.upper(), "headless": headless, "refresh_data": refresh_data, "retry_failed_only": retry_failed_only}, daemon=True); self.thread.start()

    def pause(self) -> None:
        if not self.running: return
        self.paused = True; self.pause_event.clear(); self.log("warn", "Paused after the current browser operation")

    def resume(self) -> None:
        if not self.running: return
        self.paused = False; self.pause_event.set(); self.log("info", "Resumed")

    def stop(self) -> None:
        self.stop_event.set(); self.pause_event.set(); self.log("warn", "Stop requested")

    def _collect_wanted(self, driver, *, year: int, code: str, max_pages: int) -> str | None:
        for _ in range(max_pages):
            url = _page_links(driver, {code}, year).get(f"{year}:{code}")
            if url:
                return url
            if not _click_text(driver, ["Next", "次へ", "次"]):
                break
            time.sleep(.6)
        return None

    def _search(self, driver, *, year: int, code: str, subject: str) -> tuple[str | None, str]:
        for attempt in range(2):
            if attempt: driver.get(PORTAL_URL); time.sleep(.7)
            if not _submit_search(driver, code, "code"): continue
            url = self._collect_wanted(driver, year=year, code=code, max_pages=4)
            if url: return url, "class-code"
        if subject:
            driver.get(PORTAL_URL); time.sleep(.7)
            if _submit_search(driver, subject, "subject"):
                url = self._collect_wanted(driver, year=year, code=code, max_pages=10)
                if url: return url, "subject-fallback"
        return None, "not-found"

    def _run(self, *, college: str, headless: bool, refresh_data: bool, retry_failed_only: bool) -> None:
        driver = None
        try:
            data = self.ensure_dataset(college, refresh=refresh_data); year = int(data["academicYear"]); mapping = load_mapping(self.output_file)
            if retry_failed_only:
                queue = [c for c in data["classes"] if f"{year}:{c['classCode']}" in self.failed]
            else:
                queue = [c for c in data["classes"] if f"{year}:{c['classCode']}" not in mapping]
            self.log("info", f"Queue: {len(queue)} Class codes; already stored: {len(mapping)}")
            if not queue: self.log("ok", "Nothing to collect"); return
            driver = _make_driver(headless=headless); driver.get(PORTAL_URL); time.sleep(.8); self.log("ok", f"Browser started ({'headless' if headless else 'visible'})")
            for index, item in enumerate(queue, 1):
                if self.stop_event.is_set(): break
                self.pause_event.wait()
                if self.stop_event.is_set(): break
                code, subject = item["classCode"], item["name"]
                self.current = {"index": index, "queueTotal": len(queue), "classCode": code, "name": subject}; self._save_state(); self.log("info", f"[{index}/{len(queue)}] Class {code} · {subject}")
                try: url, method = self._search(driver, year=year, code=code, subject=subject)
                except Exception as exc:
                    url, method = None, "exception"; self.log("error", f"Class {code}: {exc}")
                    try: driver.get(PORTAL_URL)
                    except Exception: pass
                key = f"{year}:{code}"
                if url and valid_direct_url(url, year, code):
                    mapping[key] = url; save_mapping(self.output_file, mapping); self.failed.pop(key, None); self._save_state(); self.log("ok", f"Class {code}: saved ({method})")
                else:
                    self.failed[key] = method; self._save_state(); self.log("error", f"Class {code}: direct link not found ({method})")
            status = self.status(college)
            self.log("warn" if status["remaining"] else "ok", f"Pass finished: {status['mapped']}/{status['total']} mapped, {status['failed']} failed")
        except Exception as exc:
            self.last_error = str(exc); self.log("error", str(exc))
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
            self.running = self.paused = False; self.current = None; self._save_state()

    def status(self, college: str | None = None) -> dict[str, Any]:
        college = (college or self.college or "APM").upper(); data = self._cached_dataset(college); mapping = load_mapping(self.output_file)
        rows=[]; total=mapped=remaining=0; year=None; term="Class list not loaded"
        if data:
            year=int(data["academicYear"]); term=data["term"]; total=len(data["classes"])
            for item in data["classes"]:
                code=item["classCode"]; key=f"{year}:{code}"; url=mapping.get(key, ""); is_mapped=bool(url); mapped += int(is_mapped); remaining += int(not is_mapped)
                rows.append({**item, "status": "mapped" if is_mapped else ("failed" if key in self.failed else "pending"), "url": url, "failure": self.failed.get(key, "")})
        return {"ok": True, "college": college, "term": term, "academicYear": year, "running": self.running, "paused": self.paused, "current": self.current, "total": total, "mapped": mapped, "remaining": remaining, "failed": sum(r["status"]=="failed" for r in rows), "progress": round(mapped/total*100,1) if total else 0, "lastError": self.last_error, "outputFile": "data/syllabus_links.json", "rows": rows, "logs": self.logs[-350:]}
