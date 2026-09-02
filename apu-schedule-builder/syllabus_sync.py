from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

PORTAL_URL = "https://syllabus.apu.ac.jp/syllabus/s/?language=en_US"
DIRECT_RE = re.compile(r'https?://syllabus\.apu\.ac\.jp/syllabus/s/a-syllabus/[A-Za-z0-9]+/(20\d{2})(\d{4,6})(?:\?[^\"\'< >\s]*)?'.replace('< >','<>'))


def direct_link_key(url: str) -> str | None:
    m = DIRECT_RE.search(html.unescape(url or ""))
    return f"{m.group(1)}:{m.group(2)}" if m else None


def extract_direct_links(raw: str, wanted: set[str] | None = None, year: int | None = None) -> dict[str, str]:
    text = html.unescape(raw or "").replace("\\/", "/")
    found: dict[str, str] = {}
    for m in DIRECT_RE.finditer(text):
        y, code = int(m.group(1)), m.group(2)
        if year is not None and y != year:
            continue
        if wanted is not None and code not in wanted:
            continue
        url = m.group(0).replace("&amp;", "&")
        found[f"{y}:{code}"] = url
    return found


def _load_mapping(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def _save_mapping(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(mapping.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _deep_elements(driver, selector: str):
    """Return elements matching selector across open Shadow DOM roots.

    Salesforce Experience Cloud / Lightning frequently renders the visible controls
    inside nested shadow roots, where Selenium's normal find_elements() cannot see
    them. execute_script can return those DOM nodes as WebElements.
    """
    try:
        return driver.execute_script("""
            const selector = arguments[0];
            const out = [];
            const seen = new Set();
            function visit(root) {
                if (!root || !root.querySelectorAll) return;
                for (const el of root.querySelectorAll(selector)) {
                    if (!seen.has(el)) { seen.add(el); out.push(el); }
                }
                for (const el of root.querySelectorAll('*')) {
                    if (el.shadowRoot) visit(el.shadowRoot);
                }
            }
            visit(document);
            return out;
        """, selector) or []
    except Exception:
        return []


def _deep_text(driver, element) -> str:
    try:
        return str(driver.execute_script("""
            const start = arguments[0];
            const parts = [];
            const seen = new Set();
            function add(v) {
                v = (v || '').toString().replace(/\\s+/g, ' ').trim();
                if (v && !seen.has(v)) { seen.add(v); parts.push(v); }
            }
            let e = start;
            let hops = 0;
            while (e && hops++ < 7) {
                add(e.getAttribute && e.getAttribute('aria-label'));
                add(e.getAttribute && e.getAttribute('placeholder'));
                add(e.getAttribute && e.getAttribute('name'));
                add(e.getAttribute && e.getAttribute('title'));
                add(e.id);
                if (hops <= 2) add(e.innerText || e.textContent);
                if (e.labels) for (const label of e.labels) add(label.innerText || label.textContent);
                const root = e.getRootNode && e.getRootNode();
                if (root && root.host) e = root.host;
                else e = e.parentElement;
            }
            return parts.join(' ').slice(0, 2400);
        """, element) or "")
    except Exception:
        try:
            return " ".join(filter(None, [element.text, element.get_attribute("aria-label"), element.get_attribute("placeholder"), element.get_attribute("name")])).strip()
        except Exception:
            return ""


def _click_text(driver, words: Iterable[str]) -> bool:
    wanted = [w.lower() for w in words]
    selector = "a,button,[role='button'],[role='menuitem'],[tabindex='0'],lightning-button,lightning-menu-item"
    candidates = _deep_elements(driver, selector)
    scored = []
    for el in candidates:
        text = _deep_text(driver, el).lower()
        if not text:
            continue
        score = max((12 if text == w else 7 if text.startswith(w) else 5 if w in text else 0) for w in wanted)
        if score:
            scored.append((score, len(text), el))
    for _, _, el in sorted(scored, key=lambda x: (-x[0], x[1])):
        try:
            if el.is_displayed() and el.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", el)
                time.sleep(0.8)
                return True
        except Exception:
            continue
    return False


def _input_candidates(driver):
    out = []
    selector = "input:not([type='hidden']),textarea,[role='searchbox'],[role='textbox'],[contenteditable='true']"
    for el in _deep_elements(driver, selector):
        try:
            if not el.is_displayed() or not el.is_enabled():
                continue
            out.append((el, _deep_text(driver, el)))
        except Exception:
            continue
    return out


def _score_input(context: str, mode: str) -> int:
    t = context.lower()
    if mode == "subject":
        strong = ["subject/class", "subject name", "class name", "course name", "科目名", "講義名称", "授業名"]
        weak = ["subject", "course", "class", "科目", "講義"]
    else:
        strong = ["class code", "course code", "授業コード", "講義コード", "クラスコード"]
        weak = ["code", "コード"]
    score = sum(20 for k in strong if k in t) + sum(4 for k in weak if k in t)
    if "instructor" in t or "teacher" in t or "教員" in t:
        score -= 15
    return score


def _find_input(driver, mode: str):
    raw = _input_candidates(driver)
    candidates = [(_score_input(ctx, mode), el) for el, ctx in raw]
    scored = [(score, el) for score, el in candidates if score > 0]
    if scored:
        return max(scored, key=lambda x: x[0])[1]

    # Salesforce occasionally labels the one general search box only as
    # "Keyword". Use it only when there is a single safe text box rather than
    # guessing among login/contact fields.
    safe = []
    for el, ctx in raw:
        t = ctx.lower()
        try:
            input_type = (el.get_attribute("type") or "text").lower()
        except Exception:
            input_type = "text"
        if input_type not in {"text", "search", "", "number"}:
            continue
        if any(x in t for x in ["password", "email", "username", "login", "sign in", "ログイン", "メール"]):
            continue
        safe.append(el)
    return safe[0] if len(safe) == 1 else None


def _wait_for_input(driver, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        subject = _find_input(driver, "subject")
        code = _find_input(driver, "code")
        if subject or code:
            return subject or code
        time.sleep(0.35)
    return None


def _ensure_search(driver) -> None:
    # Experience Cloud can take several seconds after document.readyState=complete
    # before Lightning mounts the actual controls.
    if _wait_for_input(driver, 5.0):
        return

    click_groups = [
        ["Syllabus Search", "Search Syllabus", "シラバス検索"],
        [
            "Search by Subject/Class", "Search from Subject/Class",
            "Search by Subject", "Search from Subject",
            "Search by Course", "Search by Class",
            "Subject/Class", "Course/Class",
            "科目・クラスから検索", "科目から検索", "講義から検索",
        ],
    ]
    for words in click_groups:
        if _click_text(driver, words) and _wait_for_input(driver, 8.0):
            return

    # One more passive wait covers slow Salesforce hydration even when the
    # navigation item was already selected on entry.
    _wait_for_input(driver, 5.0)


def _field_value(field) -> str:
    try:
        return str(field.get_attribute("value") or "").strip()
    except Exception:
        return ""


def _replace_input_value(driver, field, value: str) -> bool:
    """Replace a Lightning-backed input and verify the browser sees the new value.

    Selenium ``clear()`` can visually empty a Salesforce input while leaving the
    component's internal value unchanged. Keyboard replacement fires the same
    events as a user. The JS fallback uses the native value setter and emits
    composed input/change events for Lightning components.
    """
    value = str(value)
    try:
        from selenium.webdriver.common.keys import Keys
        field.click()
        field.send_keys(Keys.CONTROL, "a")
        field.send_keys(Keys.BACKSPACE)
        field.send_keys(value)
        time.sleep(0.08)
        if _field_value(field) == value:
            return True
    except Exception:
        pass

    try:
        driver.execute_script("""
            const el = arguments[0];
            const value = arguments[1];
            let proto = null;
            if (el instanceof HTMLInputElement) proto = HTMLInputElement.prototype;
            else if (el instanceof HTMLTextAreaElement) proto = HTMLTextAreaElement.prototype;
            const desc = proto && Object.getOwnPropertyDescriptor(proto, 'value');
            if (desc && desc.set) desc.set.call(el, value);
            else el.value = value;
            el.dispatchEvent(new InputEvent('input', {bubbles:true, composed:true, data:value, inputType:'insertText'}));
            el.dispatchEvent(new Event('change', {bubbles:true, composed:true}));
        """, field, value)
        time.sleep(0.08)
        return _field_value(field) == value
    except Exception:
        return False


def _submit_search(driver, value: str, mode: str) -> bool:
    _ensure_search(driver)
    field = _find_input(driver, mode)
    if field is None and mode == "code":
        field = _find_input(driver, "subject")
    if field is None:
        return False
    if not _replace_input_value(driver, field, value):
        return False

    # Prefer Enter on the exact field we just edited. This avoids clicking a
    # different generic Search button elsewhere in a Lightning page.
    submitted = False
    try:
        from selenium.webdriver.common.keys import Keys
        field.send_keys(Keys.ENTER)
        submitted = True
    except Exception:
        pass
    if not submitted:
        submitted = _click_text(driver, ["Search Syllabus", "Search", "シラバスを検索", "検索"])
    if not submitted:
        return False

    time.sleep(0.8)
    # A controlled Lightning input sometimes restores its previous value after
    # submit. Treat that as a failed search rather than silently repeating it.
    current = _find_input(driver, mode) or (_find_input(driver, "subject") if mode == "code" else None)
    if current is not None:
        actual = _field_value(current)
        if actual and actual != str(value):
            return False
    return True


def _page_links(driver, wanted: set[str], year: int) -> dict[str, str]:
    collected: dict[str, str] = {}
    # Search normal DOM and nested Lightning shadow roots. page_source alone
    # does not serialize shadow-root contents.
    for a in _deep_elements(driver, "a[href*='/a-syllabus/']"):
        try:
            href = a.get_attribute("href") or ""
            collected.update(extract_direct_links(href, wanted, year))
        except Exception:
            continue
    collected.update(extract_direct_links(driver.page_source, wanted, year))
    return collected


def _collect_pages(driver, wanted: set[str], year: int, max_pages: int = 60) -> dict[str, str]:
    out: dict[str, str] = {}
    seen_signatures: set[tuple[str, ...]] = set()
    for _ in range(max_pages):
        page = _page_links(driver, wanted, year)
        out.update(page)
        sig = tuple(sorted(page))
        if sig in seen_signatures:
            break
        seen_signatures.add(sig)
        if not _click_text(driver, ["Next", "次へ", "次"]):
            break
        time.sleep(0.8)
    return out


def _diagnostic_controls(driver) -> dict[str, Any]:
    controls = []
    selector = "input,textarea,button,a,[role='button'],[role='menuitem'],[role='searchbox'],[role='textbox'],[contenteditable='true']"
    for el in _deep_elements(driver, selector)[:400]:
        try:
            controls.append({
                "tag": (el.tag_name or "").lower(),
                "type": el.get_attribute("type") or "",
                "text": _deep_text(driver, el)[:500],
                "href": el.get_attribute("href") or "",
                "displayed": bool(el.is_displayed()),
                "enabled": bool(el.is_enabled()),
            })
        except Exception:
            continue
    return {
        "url": driver.current_url,
        "title": driver.title,
        "controls": controls,
    }


def _make_driver(headless: bool = False):
    from selenium import webdriver
    errors = []
    for kind in ("chrome", "edge"):
        try:
            if kind == "chrome":
                options = webdriver.ChromeOptions()
                if headless:
                    options.add_argument("--headless=new")
                options.add_argument("--window-size=1440,1100")
                options.add_argument("--disable-notifications")
                return webdriver.Chrome(options=options)
            options = webdriver.EdgeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,1100")
            return webdriver.Edge(options=options)
        except Exception as exc:
            errors.append(f"{kind}: {exc}")
    raise RuntimeError("Could not start Chrome or Edge via Selenium. " + " | ".join(errors))


def sync_links(*, sections: list[dict[str, Any]], year: int, mapping_path: Path, headless: bool = False) -> dict[str, Any]:
    wanted = {str(s.get("classCode", "")).strip() for s in sections if str(s.get("classCode", "")).strip()}
    subjects: dict[str, set[str]] = {}
    for s in sections:
        name = str(s.get("name", "")).strip()
        code = str(s.get("classCode", "")).strip()
        if name and code:
            subjects.setdefault(name, set()).add(code)

    mapping = _load_mapping(mapping_path)
    already = {key.split(":", 1)[1] for key in mapping if key.startswith(f"{year}:")}
    missing = wanted - already
    if not missing:
        return {"found": len(wanted), "total": len(wanted), "missing": [], "searchedSubjects": 0, "complete": True}

    driver = _make_driver(headless=headless)
    searched = 0
    try:
        driver.get(PORTAL_URL)
        time.sleep(2.5)
        _ensure_search(driver)
        if not (_find_input(driver, "subject") or _find_input(driver, "code")):
            raise RuntimeError(
                "APU syllabus search controls could not be detected, including inside Salesforce Shadow DOM. "
                "Diagnostic files were saved under data/syllabus_sync_debug/."
            )

        # Search by Class code first. It is slower than subject batching, but it
        # is deterministic and avoids Salesforce retaining the first subject
        # query in a controlled Lightning input. Every successful query targets
        # exactly one enrollment option.
        for code in sorted(missing):
            if not _submit_search(driver, code, "code"):
                # Re-open the public search once and retry. This also recovers
                # when the result page replaced/unmounted the previous input.
                driver.get(PORTAL_URL)
                _ensure_search(driver)
                if not _submit_search(driver, code, "code"):
                    continue
            hits = _collect_pages(driver, {code}, year)
            if hits:
                mapping.update(hits)
                missing -= {key.split(":", 1)[1] for key in hits}
                _save_mapping(mapping_path, mapping)
            if not missing:
                break

        # Only unresolved Class codes fall back to subject-name search. This is
        # useful for unusual language classes whose public search may not accept
        # the numeric code, while keeping the normal path unambiguous.
        for name, codes in sorted(subjects.items()):
            relevant = codes & missing
            if not relevant:
                continue
            if not _submit_search(driver, name, "subject"):
                continue
            searched += 1
            hits = _collect_pages(driver, relevant, year)
            if hits:
                mapping.update(hits)
                missing -= {key.split(":", 1)[1] for key in hits}
                _save_mapping(mapping_path, mapping)
            if not missing:
                break

        final = _load_mapping(mapping_path)
        resolved = {key.split(":", 1)[1] for key in final if key.startswith(f"{year}:")} & wanted
        missing_final = sorted(wanted - resolved)
        return {
            "found": len(resolved),
            "total": len(wanted),
            "missing": missing_final,
            "searchedSubjects": searched,
            "complete": not missing_final,
        }
    except Exception:
        # Keep a local diagnostic so a future APU UI change can be fixed without guessing.
        try:
            debug_dir = mapping_path.parent / "syllabus_sync_debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / "page.html").write_text(driver.page_source, encoding="utf-8")
            (debug_dir / "controls.json").write_text(
                json.dumps(_diagnostic_controls(driver), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            driver.save_screenshot(str(debug_dir / "page.png"))
        except Exception:
            pass
        raise
    finally:
        driver.quit()
