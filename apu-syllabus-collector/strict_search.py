from __future__ import annotations

import re
import time

import syllabus_sync as legacy
from mapping import parse_direct_url


class SearchURL(str):
    """Direct syllabus URL with transient evidence from a grouped result anchor."""

    def __new__(cls, value: str, group_codes=()):
        obj = str.__new__(cls, value)
        obj.group_codes = tuple(str(code) for code in group_codes)
        return obj


def _own_text(driver, element) -> str:
    try:
        return str(driver.execute_script("""
            const el = arguments[0];
            const parts = [
                el.innerText || el.textContent || '',
                el.getAttribute && el.getAttribute('aria-label'),
                el.getAttribute && el.getAttribute('title'),
                el.getAttribute && el.getAttribute('name'),
            ];
            return parts.filter(Boolean).join(' ').replace(/\\s+/g, ' ').trim();
        """, element) or "")
    except Exception:
        try:
            return " ".join(filter(None, [
                element.text,
                element.get_attribute("aria-label"),
                element.get_attribute("title"),
                element.get_attribute("name"),
            ])).strip()
        except Exception:
            return ""


def _click_search_button(driver) -> bool:
    labels = {"search", "search syllabus", "syllabus search", "検索", "シラバス検索", "シラバスを検索"}
    candidates = []
    selector = "button,input[type='submit'],input[type='button'],[role='button'],lightning-button"
    for element in legacy._deep_elements(driver, selector):
        try:
            if not element.is_displayed() or not element.is_enabled():
                continue
            text = _own_text(driver, element).strip().lower()
            value = str(element.get_attribute("value") or "").strip().lower()
            label = text or value
            if label in labels:
                preferred = label in {"search syllabus", "syllabus search", "シラバスを検索", "シラバス検索"}
                candidates.append((0 if preferred else 1, len(label), element))
        except Exception:
            continue
    for _, _, element in sorted(candidates, key=lambda item: (item[0], item[1])):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", element)
            return True
        except Exception:
            continue
    return False


def submit_class_code_search(driver, code: str) -> bool:
    if not legacy._ensure_search(driver, "code"):
        return False
    field = legacy._find_input(driver, "code")
    if field is None:
        return False
    if not legacy._replace_input_value(driver, field, str(code)):
        return False

    # Lightning can accept ENTER without executing the search. A visible Search
    # action must actually be clicked before this attempt counts as submitted.
    if not _click_search_button(driver):
        return False

    time.sleep(0.6)
    current = legacy._find_input(driver, "code")
    if current is not None:
        actual = legacy._field_value(current)
        if actual and actual != str(code):
            return False
    return True


def current_direct_url(driver, code: str, year: int) -> str | None:
    try:
        found = legacy.extract_direct_links(str(driver.current_url or ""), {str(code)}, year)
    except Exception:
        return None
    return found.get(f"{year}:{code}")


def _group_codes(text: str) -> tuple[str, ...]:
    # APU grouped result labels use `12347:... §12348:...`. Accept the
    # backslash-escaped colon form too because copied links may contain it.
    return tuple(dict.fromkeys(re.findall(r"(?<!\d)(\d{4,6})\s*\\?:", str(text or ""))))


def grouped_anchor_url(driver, code: str, year: int) -> SearchURL | None:
    target = str(code)
    for element in legacy._deep_elements(driver, "a[href*='/a-syllabus/']"):
        try:
            if not element.is_displayed():
                continue
            href = str(element.get_attribute("href") or "").strip()
            parsed = parse_direct_url(href)
            if not parsed or parsed[0] != int(year):
                continue
            canonical = parsed[1]
            codes = _group_codes(_own_text(driver, element))
            if len(codes) >= 2 and target in codes and canonical in codes:
                return SearchURL(href, codes)
        except Exception:
            continue
    return None


def _window_handles(driver) -> list[str]:
    try:
        return list(driver.window_handles or [])
    except Exception:
        return []


def _current_window_handle(driver) -> str | None:
    try:
        return str(driver.current_window_handle)
    except Exception:
        return None


def _switch_window(driver, handle: str | None) -> bool:
    if not handle:
        return False
    try:
        driver.switch_to.window(handle)
        return True
    except Exception:
        return False


def _direct_url_from_open_windows(
    driver,
    code: str,
    year: int,
    *,
    origin_handle: str | None,
    before_handles: set[str],
) -> str | None:
    handles = _window_handles(driver)
    if not handles:
        direct = current_direct_url(driver, code, year)
        if direct:
            return direct
        links = legacy._page_links(driver, {str(code)}, year)
        return links.get(f"{year}:{code}") if links else None

    new_handles = [handle for handle in handles if handle not in before_handles]
    existing_handles = [handle for handle in handles if handle in before_handles]
    ordered = new_handles + existing_handles

    found = None
    for handle in ordered:
        if not _switch_window(driver, handle):
            continue
        direct = current_direct_url(driver, code, year)
        if direct:
            found = direct
            break
        links = legacy._page_links(driver, {str(code)}, year)
        if links:
            found = links.get(f"{year}:{code}")
            if found:
                break

    if origin_handle and origin_handle in _window_handles(driver):
        _switch_window(driver, origin_handle)
    return found


def _close_new_windows(driver, before_handles: set[str], origin_handle: str | None) -> None:
    for handle in _window_handles(driver):
        if handle in before_handles:
            continue
        if not _switch_window(driver, handle):
            continue
        try:
            driver.close()
        except Exception:
            pass
    remaining = _window_handles(driver)
    if origin_handle and origin_handle in remaining:
        _switch_window(driver, origin_handle)
    elif remaining:
        _switch_window(driver, remaining[0])


def open_result_for_code(driver, code: str, year: int, timeout: float = 4.0) -> str | None:
    token = re.compile(rf"(?<!\d){re.escape(str(code))}(?!\d)")
    selector = "a,button,[role='link'],[role='button'],tr,[role='row'],li,[data-row-key-value],[onclick]"
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        direct = current_direct_url(driver, code, year)
        if direct:
            return direct
        links = legacy._page_links(driver, {str(code)}, year)
        if links:
            return links.get(f"{year}:{code}")
        grouped = grouped_anchor_url(driver, code, year)
        if grouped:
            return grouped

        candidates = []
        for element in legacy._deep_elements(driver, selector):
            try:
                if not element.is_displayed() or not element.is_enabled():
                    continue
                text = _own_text(driver, element)
                if not token.search(text):
                    continue
                compact = " ".join(text.split())
                candidates.append((0 if compact == str(code) else 1, len(compact), element))
            except Exception:
                continue

        if not candidates:
            time.sleep(0.25)
            continue

        for _, _, element in sorted(candidates, key=lambda item: (item[0], item[1])):
            origin_handle = _current_window_handle(driver)
            before_handles = set(_window_handles(driver))
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", element)
            except Exception:
                continue
            # Once a matching result has been clicked, do not declare failure
            # before giving the opened syllabus page the full caller timeout.
            # Focused retry passes 8s here specifically for previously failed Classes.
            nav_deadline = time.monotonic() + timeout
            try:
                while time.monotonic() < nav_deadline:
                    direct = _direct_url_from_open_windows(
                        driver,
                        code,
                        year,
                        origin_handle=origin_handle,
                        before_handles=before_handles,
                    )
                    if direct:
                        return direct
                    time.sleep(0.25)
                direct = _direct_url_from_open_windows(
                    driver,
                    code,
                    year,
                    origin_handle=origin_handle,
                    before_handles=before_handles,
                )
                if direct:
                    return direct
            finally:
                _close_new_windows(driver, before_handles, origin_handle)
        return None
    return None
