"""timetable.py 테스트 — 실제 docs/my-timetable/data.js 로 확인한다.

실행: python -m unittest test_timetable -v
"""
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from timetable import JST, Timetable, file_name, safe, unique_path

NEGO = '10128'   # Negotiation Skills, Q1, 월 1·2교시
JAPAN = '13192'  # Advanced Japanese, SEM, 월·화·목·금 3교시


def jst(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=JST)


class TimetableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tt = Timetable.load()

    def test_load(self):
        self.assertEqual(len(self.tt.courses), 8)
        self.assertEqual(len(self.tt.periods), 6)
        self.assertEqual(self.tt.periods[1], ['08:45', '10:25'])

    def test_session_numbers(self):
        self.assertEqual(self.tt.session_number(NEGO, date(2026, 10, 19), 1), 5)
        self.assertEqual(self.tt.session_number(NEGO, date(2026, 10, 19), 2), 6)
        # 스포츠의 날(공휴일 수업일)도 센다
        self.assertEqual(self.tt.session_number(NEGO, date(2026, 10, 12), 1), 3)

    def test_nego_q1_total_is_14(self):
        self.assertEqual(self.tt.session_number(NEGO, date(2026, 11, 16), 2), 14)

    def test_q2_monday_has_no_nego(self):
        self.assertEqual(self.tt.slots_on(date(2026, 11, 30)), [(3, JAPAN)])

    def test_non_class_days(self):
        for d in [date(2026, 10, 17), date(2026, 10, 18), date(2026, 11, 24),
                  date(2026, 11, 26), date(2026, 12, 25), date(2027, 2, 2)]:
            self.assertEqual(self.tt.slots_on(d), [], d)

    def test_winter_break_skipped(self):
        before = self.tt.session_number(JAPAN, date(2026, 12, 22), 3)  # 화, 방학 전 마지막 일본어
        after = self.tt.session_number(JAPAN, date(2027, 1, 7), 3)     # 목, 방학 후 첫 일본어
        self.assertEqual(after, before + 1)

    def test_match_both_periods(self):
        m = self.tt.match(jst(2026, 10, 19, 8, 40), jst(2026, 10, 19, 12, 20))
        self.assertEqual((m.code, m.periods, m.sessions), (NEGO, [1, 2], [5, 6]))
        self.assertEqual(m.title, '네고시에이션 스킬')

    def test_match_one_period(self):
        m = self.tt.match(jst(2026, 10, 19, 8, 50), jst(2026, 10, 19, 10, 20))
        self.assertEqual(m.sessions, [5])

    def test_match_none(self):
        self.assertIsNone(self.tt.match(jst(2026, 10, 19, 14, 30), jst(2026, 10, 19, 15, 0)))
        # 3교시와 10분만 겹침
        self.assertIsNone(self.tt.match(jst(2026, 10, 19, 12, 20), jst(2026, 10, 19, 12, 40)))

    def test_match_picks_course_with_most_overlap(self):
        # 2교시 끝 30분 + 3교시 전체 → 일본어
        m = self.tt.match(jst(2026, 10, 19, 11, 45), jst(2026, 10, 19, 14, 10))
        self.assertEqual((m.code, m.periods), (JAPAN, [3]))

    def test_preview(self):
        m = self.tt.preview(jst(2026, 10, 19, 8, 40))
        self.assertEqual((m.code, m.sessions), (NEGO, [5, 6]))
        self.assertIsNone(self.tt.preview(jst(2026, 10, 19, 8, 30)))
        self.assertIsNone(self.tt.preview(jst(2026, 10, 19, 19, 0)))

    def test_status(self):
        self.assertEqual(self.tt.status(jst(2026, 10, 19, 9, 0)), '지금 · 네고시에이션 스킬 · 1교시 · J103')
        self.assertEqual(self.tt.status(jst(2026, 10, 19, 12, 20)), '다음 · 12:30 일본어 상급 · FⅡ230')
        self.assertEqual(self.tt.status(jst(2026, 10, 19, 19, 0)), '오늘 남은 수업 없음')
        self.assertEqual(self.tt.status(jst(2026, 10, 18, 9, 0)), '오늘 수업 없음')


class LoadLatestTest(unittest.TestCase):
    def test_offline_falls_back_to_cache_then_bundled(self):
        import timetable
        saved = timetable.DATA_JS, timetable.SITE_DATA_JS, timetable.BUNDLED_DATA_JS
        real = timetable.DATA_JS
        try:
            with tempfile.TemporaryDirectory() as tmp:
                timetable.DATA_JS = Path(tmp) / 'no-repo.js'           # exe 처럼 저장소 밖
                timetable.SITE_DATA_JS = 'http://127.0.0.1:9/data.js'   # 네트워크 실패
                timetable.BUNDLED_DATA_JS = real
                cache = Path(tmp) / 'cache.js'
                tt, src = Timetable.load_latest(cache)
                self.assertEqual((len(tt.courses), src), (8, 'exe 내장본(오프라인)'))
                cache.write_text(real.read_text(encoding='utf-8'), encoding='utf-8')
                tt, src = Timetable.load_latest(cache)
                self.assertEqual((len(tt.courses), src), (8, '마지막 저장본(오프라인)'))
        finally:
            timetable.DATA_JS, timetable.SITE_DATA_JS, timetable.BUNDLED_DATA_JS = saved


class NameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tt = Timetable.load()

    def test_class_name(self):
        m = self.tt.match(jst(2026, 10, 19, 8, 40), jst(2026, 10, 19, 12, 20))
        self.assertEqual(file_name(m, jst(2026, 10, 19, 8, 40)),
                         ('네고시에이션 스킬 2026-10-19 (5·6회차).mp3', '네고시에이션 스킬'))

    def test_other_name(self):
        self.assertEqual(file_name(None, jst(2026, 10, 19, 14, 30)), ('녹음 2026-10-19 14-30.mp3', None))

    def test_safe(self):
        self.assertEqual(safe('a/b:c*?"<>|d\\e'), 'abcde')

    def test_unique_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertEqual(unique_path(folder, 'x.mp3').name, 'x.mp3')
            (folder / 'x.mp3').touch()
            self.assertEqual(unique_path(folder, 'x.mp3').name, 'x (2).mp3')
            (folder / 'x (2).mp3').touch()
            self.assertEqual(unique_path(folder, 'x.mp3').name, 'x (3).mp3')


if __name__ == '__main__':
    unittest.main()
