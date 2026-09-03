import unittest
from unittest.mock import patch

import strict_search


URL = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/202612077?language=en_US"
PORTAL = "https://syllabus.apu.ac.jp/syllabus/s/?language=en_US"


class Row:
    def is_displayed(self):
        return True

    def is_enabled(self):
        return True


class SwitchTo:
    def __init__(self, driver):
        self.driver = driver

    def window(self, handle):
        if handle not in self.driver._handles:
            raise RuntimeError("missing handle")
        self.driver._current = handle


class NewTabDriver:
    def __init__(self):
        self._handles = ["search"]
        self._current = "search"
        self.urls = {"search": PORTAL}
        self.switch_to = SwitchTo(self)
        self.row = Row()
        self.closed = []

    @property
    def current_url(self):
        return self.urls[self._current]

    @property
    def current_window_handle(self):
        return self._current

    @property
    def window_handles(self):
        return list(self._handles)

    def close(self):
        handle = self._current
        self.closed.append(handle)
        self._handles.remove(handle)
        self._current = self._handles[0]

    def execute_script(self, script, *args):
        if "const selector = arguments[0]" in script:
            return [self.row]
        if "const el = arguments[0]" in script:
            return "Class Code 12077 Undergraduate Thesis AF"
        if "scrollIntoView" in script:
            if "detail" not in self._handles:
                self._handles.append("detail")
                self.urls["detail"] = URL
            return None
        return None


class SameTabDriver(NewTabDriver):
    def execute_script(self, script, *args):
        if "const selector = arguments[0]" in script:
            return [self.row]
        if "const el = arguments[0]" in script:
            return "Class Code 12077 Undergraduate Thesis AF"
        if "scrollIntoView" in script:
            self.urls["search"] = URL
            return None
        return None


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class SlowNewTabDriver(NewTabDriver):
    def __init__(self, clock):
        super().__init__()
        self.clock = clock
        self.opened_at = None

    @property
    def current_url(self):
        if self._current == "detail":
            if self.opened_at is not None and self.clock.now - self.opened_at >= 5.0:
                return URL
            return "about:blank"
        return self.urls[self._current]

    def execute_script(self, script, *args):
        if "const selector = arguments[0]" in script:
            return [self.row]
        if "const el = arguments[0]" in script:
            return "Class Code 12077 Undergraduate Thesis AF"
        if "scrollIntoView" in script:
            if "detail" not in self._handles:
                self._handles.append("detail")
                self.urls["detail"] = "about:blank"
                self.opened_at = self.clock.now
            return None
        return None


class NewTabCaptureTests(unittest.TestCase):
    def test_result_opened_in_new_tab_is_captured_and_tab_is_closed(self):
        driver = NewTabDriver()
        with patch.object(strict_search.time, "sleep"):
            found = strict_search.open_result_for_code(driver, "12077", 2026)
        self.assertEqual(found, URL)
        self.assertEqual(driver.window_handles, ["search"])
        self.assertEqual(driver.current_window_handle, "search")
        self.assertEqual(driver.closed, ["detail"])

    def test_same_tab_navigation_still_works(self):
        driver = SameTabDriver()
        with patch.object(strict_search.time, "sleep"):
            found = strict_search.open_result_for_code(driver, "12077", 2026)
        self.assertEqual(found, URL)
        self.assertEqual(driver.window_handles, ["search"])
        self.assertEqual(driver.closed, [])

    def test_focused_timeout_waits_for_slow_opened_url_before_failure(self):
        clock = FakeClock()
        driver = SlowNewTabDriver(clock)
        with patch.object(strict_search.time, "monotonic", side_effect=clock.monotonic), \
             patch.object(strict_search.time, "sleep", side_effect=clock.sleep):
            found = strict_search.open_result_for_code(driver, "12077", 2026, timeout=8.0)
        self.assertEqual(found, URL)
        self.assertGreaterEqual(clock.now, 5.0)
        self.assertEqual(driver.window_handles, ["search"])
        self.assertEqual(driver.closed, ["detail"])


if __name__ == "__main__":
    unittest.main()
