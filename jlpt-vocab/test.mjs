// node jlpt-vocab/test.mjs — 통과하면 "ok"만 출력한다
import assert from 'node:assert/strict';
import {
  MAX_IVL, AGAIN, HARD, GOOD, dayNum, parseDay, isoDay, newState, knownState,
  grade, newPerDay, quota, rollDay, buildQueue,
} from '../docs/jlpt-vocab/sched.js';
import { DEFAULT_SETTINGS, toBackup, fromBackup } from '../docs/jlpt-vocab/store.js';

// 날짜: 새벽 4시 전은 전날
assert.equal(dayNum(new Date(2026, 9, 6, 3, 59)), parseDay('2026-10-05'));
assert.equal(dayNum(new Date(2026, 9, 6, 4, 0)), parseDay('2026-10-06'));
assert.equal(parseDay('2026-12-06') - parseDay('2026-10-06'), 61);
assert.equal(isoDay(parseDay('2026-12-06')), '2026-12-06');

// 평가
const T = 1000;
assert.deepEqual(newState(), ['new', 0, 0, 2.5, 0]);
assert.deepEqual(knownState(), ['known', 0, 0, 2.5, 0]);
assert.deepEqual(grade(newState(), GOOD, T), ['review', T + 1, 1, 2.5, 0]);
assert.deepEqual(grade(['review', T, 1, 2.5, 0], GOOD, T), ['review', T + 3, 3, 2.5, 0]);
assert.deepEqual(grade(['review', T, 3, 2.5, 0], GOOD, T), ['review', T + 8, 8, 2.5, 0]);
assert.deepEqual(grade(['review', T, 10, 2.5, 0], GOOD, T), ['review', T + MAX_IVL, MAX_IVL, 2.5, 0]);
assert.deepEqual(grade(['review', T, 10, 2.5, 0], AGAIN, T), ['review', T + 1, 1, 2.3, 1]);
assert.deepEqual(grade(['review', T, 5, 2.5, 0], HARD, T), ['review', T + 6, 6, 2.35, 0]);
assert.deepEqual(grade(newState(), HARD, T), ['review', T + 1, 1, 2.35, 0]);
assert.equal(grade(['review', T, 1, 1.4, 2], AGAIN, T)[3], 1.3);
assert.equal(grade(['review', T, 1, 1.3, 2], HARD, T)[3], 1.3);

// 하루 신규량
assert.equal(newPerDay(3000, 0, 55, 7), 63);
assert.equal(newPerDay(3000, 0, 7, 7), 0);
assert.equal(newPerDay(3000, 0, 3, 7), 0);
assert.equal(newPerDay(0, 0, 55, 7), 0);
const today = parseDay('2026-10-06');
const s0 = { exam: '2026-12-06', buffer: 7, today: null, quotaToday: 0, newDoneToday: 9 };
assert.equal(quota(3000, today, { ...s0, newDoneToday: 0 }), 56);   // ceil(3000 / 54)
assert.equal(quota(2990, today, { ...s0, newDoneToday: 10 }), 56);  // 오늘 한 것 포함
const s1 = rollDay(s0, today, 3000);
assert.deepEqual(s1, { ...s0, today, quotaToday: 56, newDoneToday: 0 });
assert.equal(rollDay(s1, today, 1), s1);

// 큐: 기한 된 복습(due 순) → 신규(keys 순, 개수 제한). known·미분류·미래 복습 제외
const progress = {
  a: ['new', 0, 0, 2.5, 0], b: ['review', T - 1, 1, 2.5, 0], c: ['known', 0, 0, 2.5, 0],
  d: ['new', 0, 0, 2.5, 0], e: ['review', T - 3, 1, 2.5, 0], f: ['review', T + 1, 1, 2.5, 0],
  g: ['new', 0, 0, 2.5, 0],
};
assert.deepEqual(buildQueue(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'x'], progress, T, 2), ['e', 'b', 'a', 'd']);
assert.deepEqual(buildQueue(['a', 'b'], progress, T, 0), ['b']);

// 백업: 왕복, 깨진 JSON, 다른 앱 파일, 잘못된 progress, 잘못된 시험일
const db = { progress: { 'a|あ': ['review', 5, 3, 2.5, 0] }, edits: { 'a|あ': '뜻' }, settings: { ...DEFAULT_SETTINGS, buffer: 5 } };
assert.deepEqual(fromBackup(toBackup(db)), db);
assert.equal(fromBackup('{not json'), null);
assert.equal(fromBackup(JSON.stringify({ app: 'workout-timer', v: 1 })), null);
const bad = (patch) => fromBackup(JSON.stringify({ ...JSON.parse(toBackup(db)), ...patch }));
assert.equal(bad({ progress: { k: ['review', 1, 1] } }), null);
assert.equal(bad({ progress: { k: ['oops', 1, 1, 2.5, 0] } }), null);
assert.equal(bad({ progress: [] }), null);
assert.equal(bad({ settings: { exam: '12/06' } }), null);
// 예전 백업에 없는 설정 키는 기본값으로 채운다
assert.deepEqual(bad({ settings: { exam: '2026-12-06' } }).settings, DEFAULT_SETTINGS);

console.log('ok');
