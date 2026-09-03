from __future__ import annotations

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


class CollectionManager(BaseCollectionManager):
    """Runtime collector with strict Class-code search and fixed browser partitions."""

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

    @staticmethod
    def _partition_items(items: list[dict], worker_total: int) -> list[list[tuple[int, dict]]]:
        """Split work into balanced, contiguous, non-overlapping worker parts."""
        if not items or worker_total <= 0:
            return []
        worker_total = min(worker_total, len(items))
        base, extra = divmod(len(items), worker_total)
        parts: list[list[tuple[int, dict]]] = []
        offset = 0
        for worker_index in range(worker_total):
            size = base + (1 if worker_index < extra else 0)
            part = [(index + 1, items[index]) for index in range(offset, offset + size)]
            parts.append(part)
            offset += size
        return parts

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
        part: list[tuple[int, dict]],
        *,
        queue_total: int,
        year: int,
        mapping: dict[str, str],
        headless: bool,
    ) -> None:
        label = f"W{worker_id:02d}"
        driver = None
        try:
            # Stagger startup so Selenium Manager and Chromium do not all initialize at once.
            time.sleep((worker_id - 1) * 0.2)
            driver = self._open_browser(worker_id, headless=headless)

            for part_index, (global_index, item) in enumerate(part, 1):
                if self.stop_event.is_set():
                    break
                self.pause_event.wait()
                if self.stop_event.is_set():
                    break

                code, subject = item["classCode"], item["name"]
                current = {
                    "worker": label,
                    "index": global_index,
                    "queueTotal": queue_total,
                    "partIndex": part_index,
                    "partTotal": len(part),
                    "classCode": code,
                    "name": subject,
                }
                with self.lock:
                    self.active_workers[worker_id] = current
                    self.current = current
                    self._save_state()
                self.log("info", f"[{label} P{part_index}/{len(part)}] [{global_index}/{queue_total}] Class {code} · {subject}")

                url = None
                method = "exception"
                browser_restarts = 0
                while not self.stop_event.is_set():
                    try:
                        url, method = self._search(driver, year=year, code=code, worker=label)
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
                        save_mapping(self.output_file, mapping)
                        self.failed.pop(key, None)
                        self.log("ok", f"[{label}] Class {code}: saved ({method})")
                    elif not self.stop_event.is_set():
                        self.failed[key] = method
                        self.log("error", f"[{label}] Class {code}: direct link not found ({method})")
                    self.active_workers.pop(worker_id, None)
                    self._save_state()

                if driver is None and not self.stop_event.is_set():
                    # This worker could not recover its browser. Leave the rest of its fixed part pending.
                    remaining = len(part) - part_index
                    if remaining:
                        self.log("warn", f"[{label}] Worker stopped; {remaining} Class codes in its part remain pending")
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
                items = [c for c in data["classes"] if f"{year}:{c['classCode']}" in self.failed]
            else:
                items = [c for c in data["classes"] if f"{year}:{c['classCode']}" not in mapping]

            self.log("info", f"Queue: {len(items)} Class codes; already stored: {len(mapping)}")
            if not items:
                self.log("ok", "Nothing to collect")
                return

            worker_total = min(self.worker_count, len(items))
            parts = self._partition_items(items, worker_total)
            self.log("info", f"Launching {worker_total} fixed browser parts")
            for worker_id, part in enumerate(parts, 1):
                first, last = part[0][0], part[-1][0]
                self.log("info", f"[W{worker_id:02d}] Assigned part {first}-{last} ({len(part)} Class codes)")

            workers = [
                threading.Thread(
                    target=self._browser_worker,
                    args=(worker_id, part),
                    kwargs={
                        "queue_total": len(items),
                        "year": year,
                        "mapping": mapping,
                        "headless": headless,
                    },
                    daemon=True,
                    name=f"apu-syllabus-{worker_id:02d}",
                )
                for worker_id, part in enumerate(parts, 1)
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
