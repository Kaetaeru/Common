// localStorage 저장과 백업 파일. 같은 도메인의 다른 Common 앱과 섞이지 않게 키에 접두사를 붙인다.
const PREFIX = 'jlpt-vocab:';
const STATES = ['new', 'review', 'known'];

export const DEFAULT_SETTINGS = {
  exam: '2026-12-06', buffer: 7, lastBackup: null, today: null, quotaToday: 0, newDoneToday: 0,
};

const isObj = (x) => !!x && typeof x === 'object' && !Array.isArray(x);

function read(key, fallback) {
  try { return JSON.parse(localStorage.getItem(PREFIX + key)) ?? fallback; } catch { return fallback; }
}

export function load() {
  return {
    progress: read('progress', {}),
    edits: read('edits', {}),
    settings: { ...DEFAULT_SETTINGS, ...read('settings', {}) },
  };
}

// 용량 초과 등으로 실패하면 false. 화면에서 백업을 권한다.
export function save(db, ...keys) {
  try {
    for (const k of keys) localStorage.setItem(PREFIX + k, JSON.stringify(db[k]));
    return true;
  } catch {
    return false;
  }
}

export const toBackup = (db) =>
  JSON.stringify({ app: 'jlpt-vocab', v: 1, progress: db.progress, edits: db.edits, settings: db.settings });

// 형식이 맞으면 데이터, 아니면 null. null이면 기존 데이터를 건드리지 않는다.
export function fromBackup(text) {
  let o;
  try { o = JSON.parse(text); } catch { return null; }
  if (!isObj(o) || o.app !== 'jlpt-vocab' || o.v !== 1) return null;
  if (!isObj(o.progress) || !isObj(o.edits) || !isObj(o.settings)) return null;
  for (const s of Object.values(o.progress)) {
    if (!Array.isArray(s) || s.length !== 5 || !STATES.includes(s[0]) || !s.slice(1).every(Number.isFinite)) return null;
  }
  if (!Object.values(o.edits).every((v) => typeof v === 'string')) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(o.settings.exam ?? '')) return null;
  return { progress: o.progress, edits: o.edits, settings: { ...DEFAULT_SETTINGS, ...o.settings } };
}
