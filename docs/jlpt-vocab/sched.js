// 간격 반복 스케줄러. 화면과 저장소를 모르는 순수 함수만 둔다.
// 단어 상태: [st, due, ivl, ease, lapses]  st = 'new' | 'review' | 'known'

export const MAX_IVL = 14;        // 시험 전 마지막 2주 안에 모든 단어를 한 번은 다시 본다
export const START_EASE = 2.5;
export const DAY_MS = 86400000;
export const AGAIN = 0, HARD = 1, GOOD = 2;
const CUTOFF_MS = 4 * 3600000;    // 새벽 4시 전은 전날로 친다

export function dayNum(date) {
  const d = new Date(date.getTime() - CUTOFF_MS);
  return Math.round(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY_MS);
}

export function parseDay(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return Math.round(Date.UTC(y, m - 1, d) / DAY_MS);
}

export const isoDay = (n) => new Date(n * DAY_MS).toISOString().slice(0, 10);
export const newState = () => ['new', 0, 0, START_EASE, 0];
export const knownState = () => ['known', 0, 0, START_EASE, 0];

export function grade(state, g, today) {
  let [, , ivl, ease, lapses] = state;
  if (g === AGAIN) { ivl = 1; ease -= 0.2; lapses += 1; }
  else if (g === HARD) { ivl = Math.max(1, Math.round(ivl * 1.2)); ease -= 0.15; }
  else ivl = ivl === 0 ? 1 : ivl === 1 ? 3 : Math.round(ivl * ease);
  ivl = Math.min(ivl, MAX_IVL);
  ease = Math.max(1.3, Math.round(ease * 100) / 100);
  return ['review', today + ivl, ivl, ease, lapses];
}

// 남은 신규를 (시험일 - 버퍼)까지 고르게 나눈다
export function newPerDay(remainingNew, today, exam, buffer) {
  const days = exam - today - buffer;
  return days <= 0 || remainingNew <= 0 ? 0 : Math.ceil(remainingNew / days);
}

// 오늘 이미 시작한 신규까지 포함해서 오늘 할당량을 계산한다
export const quota = (remainingNew, today, s) =>
  newPerDay(remainingNew + s.newDoneToday, today, parseDay(s.exam), s.buffer);

export function rollDay(settings, today, remainingNew) {
  if (settings.today === today) return settings;
  const s = { ...settings, today, newDoneToday: 0 };
  s.quotaToday = quota(remainingNew, today, s);
  return s;
}

export function buildQueue(keys, progress, today, newCount) {
  const due = [], fresh = [];
  for (const k of keys) {
    const s = progress[k];
    if (!s) continue;
    if (s[0] === 'review' && s[1] <= today) due.push(k);
    else if (s[0] === 'new' && fresh.length < newCount) fresh.push(k);
  }
  due.sort((a, b) => progress[a][1] - progress[b][1]);
  return due.concat(fresh);
}
