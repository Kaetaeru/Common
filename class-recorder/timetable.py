"""내 시간표(docs/my-timetable/data.js)로 정규 수업일, 회차, 녹음 파일 이름을 정한다.

화면·소리와 무관한 순수 로직. 시간은 모두 일본 시간(JST) 기준.
정규 수업일 규칙은 docs/my-timetable/app.js 의 dayInfo 와 같다.
"""
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
DATA_JS = Path(__file__).resolve().parent.parent / 'docs' / 'my-timetable' / 'data.js'
MIN_OVERLAP = 20   # 분. 이만큼 겹친 교시만 그 수업 녹음으로 인정
PREVIEW_LEAD = 10  # 분. 교시 시작 이만큼 전부터 미리보기에 그 수업 이름


def _strip_line_comment(line):
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in '\'"':
            quote = ch
        elif line.startswith('//', i):
            return line[:i]
    return line


def js_to_json(src):
    """data.js 의 `window.TT = {...};` 객체 리터럴을 dict 로. (주석, 따옴표 없는 키, 작은따옴표, 끝 쉼표)"""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = '\n'.join(_strip_line_comment(line) for line in src.splitlines())
    body = src[src.index('{'): src.rindex('}') + 1]
    body = re.sub(r"'([^']*)'", lambda m: json.dumps(m.group(1), ensure_ascii=False), body)
    body = re.sub(r'([{,]\s*)([A-Za-z_]\w*|\d+)\s*:', r'\1"\2":', body)
    body = re.sub(r',(\s*[}\]])', r'\1', body)
    return json.loads(body)


@dataclass
class Match:
    code: str
    title: str          # 과목 한국어 이름 (data.js 의 ko)
    day: date
    periods: list[int]
    sessions: list[int]


class Timetable:
    def __init__(self, tt):
        self.cal = tt['calendar']
        self.periods = {int(k): v for k, v in tt['periods'].items()}
        self.courses = tt['courses']
        self.slots = [(d, p, str(c)) for d, p, c in tt['slots']]

    @classmethod
    def load(cls, path=DATA_JS):
        return cls(js_to_json(Path(path).read_text(encoding='utf-8')))

    def _in(self, d, rng):
        return rng[0] <= d.isoformat() <= rng[1]

    def quarter(self, d):
        """정규 수업일이면 1 또는 2, 아니면 0."""
        c = self.cal
        if d.weekday() >= 5 or d.isoformat() in c['makeupDays'] or any(self._in(d, b) for b in c['breaks']):
            return 0
        return 1 if self._in(d, c['q1']) else 2 if self._in(d, c['q2']) else 0

    def slots_on(self, d):
        """그날 정규 수업 [(교시, class code)], 교시순."""
        q = self.quarter(d)
        if not q:
            return []
        skip = 'Q2' if q == 1 else 'Q1'
        return sorted((p, c) for wd, p, c in self.slots if wd == d.isoweekday() and self.courses[c]['term'] != skip)

    def session_number(self, code, d, period):
        """교시마다 1회로 센 회차. 1쿼터 시작일부터 센다."""
        n = 0
        day = date.fromisoformat(self.cal['q1'][0])
        while day < d:
            n += sum(c == code for _, c in self.slots_on(day))
            day += timedelta(days=1)
        return n + sum(c == code and p <= period for p, c in self.slots_on(d))

    def _span(self, d, p):
        def at(hm):
            h, m = map(int, hm.split(':'))
            return datetime(d.year, d.month, d.day, h, m, tzinfo=JST)
        a, b = self.periods[p]
        return at(a), at(b)

    def _result(self, code, d, periods):
        return Match(code, self.courses[code]['ko'], d, periods, [self.session_number(code, d, p) for p in periods])

    def match(self, start, end):
        """녹음 구간과 20분 이상 겹친 교시 중, 겹친 시간 합이 가장 큰 과목."""
        s, e = start.astimezone(JST), end.astimezone(JST)
        d = s.date()
        hits = {}
        for p, code in self.slots_on(d):
            a, b = self._span(d, p)
            minutes = (min(e, b) - max(s, a)).total_seconds() / 60
            if minutes >= MIN_OVERLAP:
                hits.setdefault(code, []).append((p, minutes))
        if not hits:
            return None
        code = max(hits, key=lambda c: sum(m for _, m in hits[c]))
        return self._result(code, d, [p for p, _ in hits[code]])

    def preview(self, now):
        """지금 녹음을 시작하면 붙을 이름. 교시 안이거나 시작 10분 전부터, 이어지는 같은 과목 교시까지 묶는다."""
        n = now.astimezone(JST)
        d = n.date()
        slots = self.slots_on(d)
        for i, (p, code) in enumerate(slots):
            a, b = self._span(d, p)
            if a - timedelta(minutes=PREVIEW_LEAD) <= n < b:
                periods = [p]
                for p2, c2 in slots[i + 1:]:
                    if c2 != code or p2 != periods[-1] + 1:
                        break
                    periods.append(p2)
                return self._result(code, d, periods)
        return None

    def status(self, now):
        n = now.astimezone(JST)
        d = n.date()
        slots = self.slots_on(d)
        for p, code in slots:
            a, b = self._span(d, p)
            c = self.courses[code]
            if a <= n < b:
                return f"지금 · {c['ko']} · {p}교시 · {c['room']}"
            if n < a:
                return f"다음 · {a:%H:%M} {c['ko']} · {c['room']}"
        return '오늘 남은 수업 없음' if slots else '오늘 수업 없음'


def safe(s):
    return re.sub(r'[\\/:*?"<>|]', '', s).strip()


def file_name(m, start):
    """(파일 이름, 과목 폴더 이름 또는 None)"""
    if m:
        title = safe(m.title)
        return f"{title} {m.day.isoformat()} ({'·'.join(map(str, m.sessions))}회차).mp3", title
    return f"녹음 {start.astimezone(JST):%Y-%m-%d %H-%M}.mp3", None


def unique_path(folder, name):
    path = Path(folder) / name
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 2
    while path.exists():
        path = Path(folder) / f'{stem} ({i}){suffix}'
        i += 1
    return path
