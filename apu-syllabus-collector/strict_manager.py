from __future__ import annotations

import queue
import threading
import time

from manager import CollectionManager as BaseCollectionManager
from mapping import load_mapping, save_mapping, valid_direct_url
from strict_search import current_direct_url, open_result_for_code, submit_class_code_search
from syllabus_sync import PORTAL_URL, _click_text, _make_driver, _page_links


DEFAULT_WORKER_COUNT = 5
MAX_WORKER_COUNT = 10
BROWSER_START_ATTEMPTS = 3
BROWSER_RESTARTS_PER_CLASS = 2
FOCUSED_SEARCH_ATTEMPTS = 4
FOCUSED_RESULT_PAGES = 6
FOCUSED_RESULT_TIMEOUT = 8.0
FOCUSED_RELOAD_WAIT = 1.2


class CollectionManager(BaseCollectionManager):
    """Runtime collector with strict Class-code search and a shared worker queue."""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.worker_count = DEFAULT_WORKER_COUNT
        self.active_workers: dict[int, dict] = {}

    @staticmethod
    def _normalize_worker_count(value) -> int:
        try:
            count = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Browser count must be an integer from 1 to 10.") from exc
        if not 1 <= count <= MAX_WORKER_COUNT:
            raise ValueError("Browser count must be from 1 to 10.")
        return count

    def start(
        self,
        *,
        college: str,
        headless: bool = False,
        refresh_data: bool = False,
        retry_failed_only: bool = False,
        worker_count: int | None = None,
    ) -> None:
        count = self._normalize_worker_count(worker_count if worker_count is not None else self.worker_count)
        with self.lock:
            if self.running:
                raise RuntimeError("Collector is already running.")
            self.worker_count = count
            self.running, self.paused, self.last_error = True, False, ""
            self.stop_event.clear()
            self.pause_event.set()
        self.thread = threading.Thread(
            target=self._run,
            kwargs={
                "college": college.upper(),
                "headless": headless,
                "refresh_data": refresh_data,
                "retry_failed_only": retry_failed_only,
            },
            daemon=True,
        )
        self.thread.start()

    def _collect_wanted(
        self,
        driver,
        *,
        year: int,
        code: str,
        max_pages: int,
        result_timeout: float = 4.0,
    ) -> str | None:
        for _ in range(max_pages):
            url = current_direct_url(driver, code, year)
            if url:
                return url
            url = _page_links(driver, {code}, year).get(f"{year}:{code}")
            if url:
                return url
            url = open_result_for_code(driver, code, year, timeout=result_timeout)
            if url:
                return url
            if not _click_text(driver, ["Next", "次へ", "次"]):
                break
            time.sleep(0.6)
        return None

    def _search(
        self,
        driver,
        *,
        year: int,
        code: str,
        worker: str = "",
        focused: bool = False,
    ) -> tuple[str | None, str]:
        prefix = f"[{worker}] " if worker else ""
        attempts = FOCUSED_SEARCH_ATTEMPTS if focused else 2
        max_pages = FOCUSED_RESULT_PAGES if focused else 4
        result_timeout = FOCUSED_RESULT_TIMEOUT if focused else 4.0
        reload_wait = FOCUSED_RELOAD_WAIT if focused else 0.7
        mode_label = "Focused Class Code" if focused else "Class Code"
        submitted = False
        for attempt in range(attempts):
            if attempt:
                driver.get(PORTAL_URL)
                time.sleep(reload_wait)
            if not submit_class_code_search(driver, code):
                self.log(
                    "warn",
                    f"{prefix}Class {code}: {mode_label} Search button not triggered "
                    f"(attempt {attempt + 1}/{attempts})",
                )
                continue
            submitted = True
            self.log(
                "info",
                f"{prefix}Class {code}: {mode_label} Search clicked "
                f"(attempt {attempt + 1}/{attempts})",
            )
            url = self._collect_wanted(
                driver,
                year=year,
                code=code,
                max_pages=max_pages,
                result_timeout=result_timeout,
            )
            if url:
                return url, "class-code-focused" if focused else "class-code"
        return None, "class-code-result-not-found" if submitted else "class-code-search-not-triggered"

    def _open_browser(self, worker_id: int, *, headless: bool, restarted: bool = False):
        label = f"W{worker_id:02d}"
        last_error: Exception | None = None
        for attempt in range(1, BROWSER_START_ATTEMPTS + 1):
            driver = None
            try:
                driver = _make_driver(headless=headless)
                driver.get(PORTAL_URL)
                time.sleep(0.8)
                action = "restarted" if restarted else "started"
                self.log("ok", f"[{label}] Browser {action} ({'headless' if headless else 'visible'})")
                return driver
            except Exception as exc:
                last_error = exc
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                self.log("warn", f"[{label}] Browser start failed ({attempt}/{BROWSER_START_ATTEMPTS}): {exc}")
                if attempt < BROWSER_START_ATTEMPTS:
                    time.sleep(1.0)
        raise RuntimeError(f"Browser could not start after {BROWSER_START_ATTEMPTS} attempts: {last_error}")

    def _browser_worker(
        self,
        worker_id: int,
        work: queue.Queue,
        *,
        queue_total: int,
        year: int,
        mapping: dict[str, str],
        headless: bool,
        focused: bool = False,
    ) -> None:
        label = f"W{worker_id:02d}"
        driver = None
        try:
            # Stagger startup so Selenium Manager and Chromium do not all initialize at once.
            time.sleep((worker_id - 1) * 0.2)
            driver = self._open_browser(worker_id, headless=headless)

            while not self.stop_event.is_set():
                self.pause_event.wait()
                if self.stop_event.is_set():
                    break
                try:
                    global_index, item = work.get_nowait()
                except queue.Empty:
                    break

                code, subject = item["classCode"], item["name"]
                current = {
                    "worker": label,
                    "index": global_index,
                    "queueTotal": queue_total,
                    "classCode": code,
                    "name": subject,
                }
                with self.lock:
                    self.active_workers[worker_id] = current
                    self.current = current
                    self._save_state()
                self.log("info", f"[{label}] [{global_index}/{queue_total}] Class {code} · {subject}")

                try:
                    url = None
                    method = "exception"
                    browser_restarts = 0
                    while not self.stop_event.is_set():
                        try:
                            url, method = self._search(
                                driver, year=year, code=code, worker=label, focused=focused
                            )
                            break
                        except Exception as exc:
                            browser_restarts += 1
                            self.log("error", f"[{label}] Class {code}: browser session error: {exc}")
                            if driver:
                                try:
                                    driver.quit()
                                except Exception:
                                    pass
                            driver = None
                            if browser_restarts > BROWSER_RESTARTS_PER_CLASS:
                                method = "browser-session-crashed"
                                self.log("error", f"[{label}] Class {code}: browser restart limit reached")
                                break
                            self.log(
                                "warn",
                                f"[{label}] Restarting browser and retrying the same Class {code} "
                                f"({browser_restarts}/{BROWSER_RESTARTS_PER_CLASS})",
                            )
                            try:
                                driver = self._open_browser(worker_id, headless=headless, restarted=True)
                            except Exception as restart_exc:
                                method = "browser-restart-failed"
                                self.log("error", f"[{label}] Browser restart failed: {restart_exc}")
                                break

                    key = f"{year}:{code}"
                    with self.lock:
                        if url and valid_direct_url(url, year, code):
                            mapping[key] = url
                            try:
                                save_mapping(self.output_file, mapping)
                            except OSError as exc:
                                mapping.pop(key, None)
                                self.failed[key] = "save-failed"
                                self.log("error", f"[{label}] Class {code}: result found but save failed: {exc}")
                            else:
                                self.failed.pop(key, None)
                                self.log("ok", f"[{label}] Class {code}: saved ({method})")
                        elif not self.stop_event.is_set():
                            self.failed[key] = method
                            self.log("error", f"[{label}] Class {code}: direct link not found ({method})")
                        self.active_workers.pop(worker_id, None)
                        self._save_state()
                finally:
                    work.task_done()

                if driver is None and not self.stop_event.is_set():
                    self.log("warn", f"[{label}] Worker stopped; remaining shared work will be handled by other workers")
                    break
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
                items = [
                    c
                    for c in data["classes"]
                    if f"{year}:{c['classCode']}" in self.failed
                    and f"{year}:{c['classCode']}" not in mapping
                ]
                self.log(
                    "info",
                    f"Focused retry work set: {len(items)} failed Class codes only; "
                    f"already stored: {len(mapping)}",
                )
            else:
                items = [c for c in data["classes"] if f"{year}:{c['classCode']}" not in mapping]
                self.log("info", f"Work set: {len(items)} Class codes; already stored: {len(mapping)}")
            if not items:
                self.log("ok", "Nothing to collect")
                return

            work: queue.Queue = queue.Queue()
            for index, item in enumerate(items, 1):
                work.put((index, item))

            worker_total = min(self.worker_count, len(items))
            self.log("info", f"Launching {worker_total} shared-queue browser workers")
            workers = [
                threading.Thread(
                    target=self._browser_worker,
                    args=(worker_id, work),
                    kwargs={
                        "queue_total": len(items),
                        "year": year,
                        "mapping": mapping,
                        "headless": headless,
                        "focused": retry_failed_only,
                    },
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
            result["maxWorkerCount"] = MAX_WORKER_COUNT
            result["activeWorkers"] = [dict(value) for _, value in sorted(self.active_workers.items())]
        return result
