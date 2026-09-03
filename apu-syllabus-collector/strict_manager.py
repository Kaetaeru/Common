from __future__ import annotations

import queue
import threading
import time

from manager import CollectionManager as BaseCollectionManager
from mapping import load_mapping, save_mapping, valid_direct_url
from strict_search import current_direct_url, open_result_for_code, submit_class_code_search
from syllabus_sync import PORTAL_URL, _click_text, _make_driver, _page_links


WORKER_COUNT = 10


class CollectionManager(BaseCollectionManager):
    """Runtime collector with strict Class-code-only search and 10 browser workers."""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.worker_count = WORKER_COUNT
        self.active_workers: dict[int, dict] = {}

    def _collect_wanted(self, driver, *, year: int, code: str, max_pages: int) -> str | None:
        for _ in range(max_pages):
            url = current_direct_url(driver, code, year)
            if url:
                return url
            url = _page_links(driver, {code}, year).get(f"{year}:{code}")
            if url:
                return url
            url = open_result_for_code(driver, code, year)
            if url:
                return url
            if not _click_text(driver, ["Next", "次へ", "次"]):
                break
            time.sleep(0.6)
        return None

    def _search(self, driver, *, year: int, code: str, worker: str = "") -> tuple[str | None, str]:
        prefix = f"[{worker}] " if worker else ""
        submitted = False
        for attempt in range(2):
            if attempt:
                driver.get(PORTAL_URL)
                time.sleep(0.7)
            if not submit_class_code_search(driver, code):
                self.log("warn", f"{prefix}Class {code}: Class Code Search button not triggered (attempt {attempt + 1}/2)")
                continue
            submitted = True
            self.log("info", f"{prefix}Class {code}: Class Code Search clicked (attempt {attempt + 1}/2)")
            url = self._collect_wanted(driver, year=year, code=code, max_pages=4)
            if url:
                return url, "class-code"
        return None, "class-code-result-not-found" if submitted else "class-code-search-not-triggered"

    def _browser_worker(self, worker_id: int, work: queue.Queue, *, year: int, mapping: dict[str, str], headless: bool) -> None:
        label = f"W{worker_id:02d}"
        driver = None
        try:
            # Avoid asking Selenium Manager / Chrome to initialize ten processes in the exact same millisecond.
            time.sleep((worker_id - 1) * 0.15)
            driver = _make_driver(headless=headless)
            driver.get(PORTAL_URL)
            time.sleep(0.8)
            self.log("ok", f"[{label}] Browser started ({'headless' if headless else 'visible'})")

            while not self.stop_event.is_set():
                self.pause_event.wait()
                if self.stop_event.is_set():
                    break
                try:
                    index, item, queue_total = work.get_nowait()
                except queue.Empty:
                    break

                code, subject = item["classCode"], item["name"]
                current = {
                    "worker": label,
                    "index": index,
                    "queueTotal": queue_total,
                    "classCode": code,
                    "name": subject,
                }
                with self.lock:
                    self.active_workers[worker_id] = current
                    self.current = current
                    self._save_state()
                self.log("info", f"[{label}] [{index}/{queue_total}] Class {code} · {subject}")

                try:
                    url, method = self._search(driver, year=year, code=code, worker=label)
                except Exception as exc:
                    url, method = None, "exception"
                    self.log("error", f"[{label}] Class {code}: {exc}")
                    try:
                        driver.get(PORTAL_URL)
                    except Exception:
                        pass

                key = f"{year}:{code}"
                with self.lock:
                    if url and valid_direct_url(url, year, code):
                        mapping[key] = url
                        save_mapping(self.output_file, mapping)
                        self.failed.pop(key, None)
                        self.log("ok", f"[{label}] Class {code}: saved ({method})")
                    else:
                        self.failed[key] = method
                        self.log("error", f"[{label}] Class {code}: direct link not found ({method})")
                    self.active_workers.pop(worker_id, None)
                    self._save_state()
                work.task_done()
        except Exception as exc:
            self.log("error", f"[{label}] Browser worker failed: {exc}")
        finally:
            with self.lock:
                self.active_workers.pop(worker_id, None)
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _run(self, *, college: str, headless: bool, refresh_data: bool, retry_failed_only: bool) -> None:
        try:
            data = self.ensure_dataset(college, refresh=refresh_data)
            year = int(data["academicYear"])
            mapping = load_mapping(self.output_file)
            if retry_failed_only:
                items = [c for c in data["classes"] if f"{year}:{c['classCode']}" in self.failed]
            else:
                items = [c for c in data["classes"] if f"{year}:{c['classCode']}" not in mapping]

            self.log("info", f"Queue: {len(items)} Class codes; already stored: {len(mapping)}")
            if not items:
                self.log("ok", "Nothing to collect")
                return

            work: queue.Queue = queue.Queue()
            for index, item in enumerate(items, 1):
                work.put((index, item, len(items)))

            worker_total = min(self.worker_count, len(items))
            self.log("info", f"Launching {worker_total} parallel browser workers")
            workers = [
                threading.Thread(
                    target=self._browser_worker,
                    args=(worker_id, work),
                    kwargs={"year": year, "mapping": mapping, "headless": headless},
                    daemon=True,
                    name=f"apu-syllabus-{worker_id:02d}",
                )
                for worker_id in range(1, worker_total + 1)
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()

            status = self.status(college)
            self.log(
                "warn" if status["remaining"] else "ok",
                f"Pass finished: {status['mapped']}/{status['total']} mapped, {status['failed']} failed",
            )
        except Exception as exc:
            self.last_error = str(exc)
            self.log("error", str(exc))
        finally:
            with self.lock:
                self.active_workers.clear()
                self.running = self.paused = False
                self.current = None
                self._save_state()

    def status(self, college: str | None = None) -> dict:
        result = super().status(college)
        with self.lock:
            result["workerCount"] = self.worker_count
            result["activeWorkers"] = [dict(value) for _, value in sorted(self.active_workers.items())]
        return result
