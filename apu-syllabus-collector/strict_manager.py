from __future__ import annotations

import time

from manager import CollectionManager as BaseCollectionManager
from strict_search import current_direct_url, open_result_for_code, submit_class_code_search
from syllabus_sync import PORTAL_URL, _click_text, _page_links


class CollectionManager(BaseCollectionManager):
    """Runtime collector with strict Class-code-only search behavior."""

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

    def _search(self, driver, *, year: int, code: str) -> tuple[str | None, str]:
        submitted = False
        for attempt in range(2):
            if attempt:
                driver.get(PORTAL_URL)
                time.sleep(0.7)
            if not submit_class_code_search(driver, code):
                self.log("warn", f"Class {code}: Class Code Search button not triggered (attempt {attempt + 1}/2)")
                continue
            submitted = True
            self.log("info", f"Class {code}: Class Code Search clicked (attempt {attempt + 1}/2)")
            url = self._collect_wanted(driver, year=year, code=code, max_pages=4)
            if url:
                return url, "class-code"
        return None, "class-code-result-not-found" if submitted else "class-code-search-not-triggered"
