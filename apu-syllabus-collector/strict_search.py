from __future__ import annotations

import re
import time

import syllabus_sync as legacy


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
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", element)
            except Exception:
                continue
            nav_deadline = time.monotonic() + 4.0
            while time.monotonic() < nav_deadline:
                direct = current_direct_url(driver, code, year)
                if direct:
                    return direct
                links = legacy._page_links(driver, {str(code)}, year)
                if links:
                    return links.get(f"{year}:{code}")
                time.sleep(0.25)
        return None
    return None
