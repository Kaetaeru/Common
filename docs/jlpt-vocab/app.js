import {
  dayNum, parseDay, isoDay, newState, knownState, grade, buildQueue, rollDay, quota, AGAIN,
} from './sched.js';
import { load, save, toBackup, fromBackup } from './store.js';

const $ = (id) => document.getElementById(id);
const keyOf = (w) => `${w.k}|${w.r}`;
const AGAIN_GAP = 5;            // 모름 카드는 5장 뒤에 다시 나온다
const WARN_NEW_PER_DAY = 60;
const BACKUP_NAG_DAYS = 7;

let words = [];                 // words.json 그대로 (N2 → N1 순서)
let byKey = new Map();
let db = load();
let today = dayNum(new Date());

function persist(...keys) {
  if (!save(db, ...keys)) alert('저장에 실패했습니다. 설정에서 백업을 내보내 주세요.');
}

const states = () => Object.values(db.progress);
const countNew = () => states().filter((s) => s[0] === 'new').length;
const meaning = (w) => db.edits[keyOf(w)] ?? w.ko;
const answerText = (w) => (w.k === w.r ? meaning(w) : `${w.r} · ${meaning(w)}`);

function refreshDay() {
  today = dayNum(new Date());
  const s = rollDay(db.settings, today, countNew());
  if (s !== db.settings) { db.settings = s; persist('settings'); }
}

function recomputeQuota() {
  db.settings.quotaToday = quota(countNew(), today, db.settings);
  persist('settings');
}

function show(id) {
  for (const s of document.querySelectorAll('main > section')) s.hidden = s.id !== id;
  if (id === 'home') renderHome();
  if (id === 'settings') renderSettings();
}

/* ---------- 홈 ---------- */

function renderHome() {
  refreshDay();
  recomputeQuota();             // 훑어보기 중 앱을 닫아도 할당량이 맞도록
  const st = db.settings;
  const left = parseDay(st.exam) - today;
  $('dday').textContent = left > 0 ? `N1까지 D-${left}` : left === 0 ? 'N1 시험 당일' : 'N1 시험 끝';

  const due = states().filter((s) => s[0] === 'review' && s[1] <= today).length;
  const newLeft = Math.min(Math.max(0, st.quotaToday - st.newDoneToday), countNew());
  $('todayLine').textContent = `오늘 복습 ${due} · 신규 ${newLeft}`;
  $('startStudy').disabled = due + newLeft === 0;

  const notes = [];
  if (st.quotaToday > WARN_NEW_PER_DAY) {
    notes.push(`하루 신규가 ${st.quotaToday}개입니다. 훑어보기를 더 엄격하게 하거나 설정에서 버퍼를 줄여 보세요.`);
  }
  const hasProgress = states().length > 0;
  if (hasProgress && (st.lastBackup === null || today - st.lastBackup > BACKUP_NAG_DAYS)) {
    notes.push(st.lastBackup === null ? '아직 백업하지 않았습니다. 설정에서 내보내 주세요.' : '백업한 지 7일이 지났습니다. 설정에서 내보내 주세요.');
  }
  $('warn').textContent = notes.join(' ');
  $('warn').hidden = notes.length === 0;

  const p = skimProgress();
  $('startSkim').hidden = !p;
  if (p) {
    $('startSkim').className = 'accent';
    $('startSkim').textContent = hasProgress
      ? `훑어보기 계속 (N${p.lv} ${p.done}/${p.size})`
      : `훑어보기 시작 (N${p.lv} ${p.size}개)`;
  }
}

/* ---------- 훑어보기 ---------- */

let skimIdx = -1;
let skimLast = null;            // 되돌리기용 직전 키
let skimTimer = 0;              // 모른다 답 보여주기 타이머
let skimBusy = false;           // 모른다 답을 보여주는 1초 동안 입력 무시

function nextSkimIndex(from = 0) {
  for (let i = from; i < words.length; i++) if (!db.progress[keyOf(words[i])]) return i;
  return -1;
}

// 지금 훑어보는 레벨의 진행 상황. 다 끝났으면 null
function skimProgress() {
  const i = nextSkimIndex();
  if (i < 0) return null;
  const lv = words[i].lv;
  const inLv = words.filter((w) => w.lv === lv);
  return { lv, size: inLv.length, done: inLv.filter((w) => db.progress[keyOf(w)]).length };
}

function startSkim() {
  clearTimeout(skimTimer);
  skimBusy = false;
  skimIdx = nextSkimIndex();
  skimLast = null;
  show('skim');
  renderSkim();
}

function renderSkim() {
  if (skimIdx < 0) { leaveSkim(); return; }
  $('skimFront').textContent = words[skimIdx].k;
  $('skimBack').textContent = '';
  const p = skimProgress();
  $('skimCount').textContent = `N${p.lv} ${p.done}/${p.size}`;
  $('skimUndo').disabled = !skimLast;
}

function skim(known) {
  if (skimBusy || skimIdx < 0) return;
  const w = words[skimIdx];
  db.progress[keyOf(w)] = known ? knownState() : newState();
  persist('progress');
  skimLast = keyOf(w);
  const next = () => { skimBusy = false; skimIdx = nextSkimIndex(skimIdx + 1); renderSkim(); };
  if (known) { next(); return; }
  skimBusy = true;
  $('skimBack').textContent = answerText(w);
  skimTimer = setTimeout(next, 1000);
}

function undoSkim() {
  if (!skimLast || skimBusy) return;
  delete db.progress[skimLast];
  persist('progress');
  skimLast = null;
  skimIdx = nextSkimIndex();
  renderSkim();
}

// 할당량은 renderHome이 다시 계산한다
function leaveSkim() {
  show('home');
}

/* ---------- 학습 ---------- */

let queue = [];                 // { key, again } — again이면 이미 저장한 모름 카드의 재출제
let cur = null;
let revealed = false;

function startStudy() {
  refreshDay();
  const st = db.settings;
  const keys = buildQueue([...byKey.keys()], db.progress, today, Math.max(0, st.quotaToday - st.newDoneToday));
  queue = keys.map((key) => ({ key, again: false }));
  show('study');
  nextCard();
}

function nextCard() {
  cur = queue.shift() ?? null;
  revealed = false;
  $('studyBack').hidden = true;
  $('gradeRow').hidden = true;
  $('tapHint').hidden = false;
  if (!cur) {
    $('studyFront').textContent = '오늘 끝';
    $('tapHint').textContent = '탭해서 홈으로';
    $('studyCount').textContent = '';
    return;
  }
  const w = byKey.get(cur.key);
  $('studyFront').textContent = w.k;
  $('studyReading').textContent = w.k === w.r ? '' : w.r;
  $('studyKo').textContent = meaning(w);
  $('studyEn').textContent = w.en;
  $('tapHint').textContent = '탭해서 답 보기';
  $('studyCount').textContent = `남은 ${queue.length + 1}`;
}

function reveal() {
  if (!cur) { show('home'); return; }
  if (revealed) return;
  revealed = true;
  $('studyBack').hidden = false;
  $('gradeRow').hidden = false;
  $('tapHint').hidden = true;
}

function answer(g) {
  if (!cur || !revealed) return;
  const { key, again } = cur;
  if (!again) {                  // 첫 평가만 저장한다
    const was = db.progress[key];
    if (was[0] === 'new') db.settings.newDoneToday += 1;
    db.progress[key] = grade(was, g, today);
    persist('progress', 'settings');
  }
  if (g === AGAIN) queue.splice(AGAIN_GAP, 0, { key, again: true });
  nextCard();
}

function editKo(e) {
  e.stopPropagation();           // 카드 탭으로 번지지 않게
  const w = byKey.get(cur.key);
  const v = prompt('한국어 뜻 (비우면 원래 뜻)', meaning(w));
  if (v === null) return;
  const t = v.trim();
  if (!t || t === w.ko) delete db.edits[cur.key];
  else db.edits[cur.key] = t;
  persist('edits');
  $('studyKo').textContent = meaning(w);
}

/* ---------- 설정·통계 ---------- */

function renderSettings() {
  const n = (st) => states().filter((s) => s[0] === st).length;
  const seen = words.filter((w) => db.progress[keyOf(w)]).length;
  const st = db.settings;
  const rows = [
    ['전체 단어', words.length],
    ['훑어보기 안 함', words.length - seen],
    ['제외 (안다)', n('known')],
    ['신규 대기', n('new')],
    ['학습 중', n('review')],
    ['오늘 신규 할당', st.quotaToday],
    ['마지막 백업', st.lastBackup === null ? '없음' : isoDay(st.lastBackup)],
  ];
  $('stats').replaceChildren(...rows.flatMap(([k, v]) => {
    const dt = document.createElement('dt'); dt.textContent = k;
    const dd = document.createElement('dd'); dd.textContent = v;
    return [dt, dd];
  }));
  $('examInput').value = st.exam;
  $('bufferInput').value = st.buffer;
}

function changeSettings() {
  const exam = $('examInput').value;
  const buffer = Number($('bufferInput').value);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(exam) || $('bufferInput').value === '' || !Number.isInteger(buffer) || buffer < 0 || buffer > 30) { renderSettings(); return; }
  db.settings.exam = exam;
  db.settings.buffer = buffer;
  recomputeQuota();
  renderSettings();
}

async function exportBackup() {
  const name = `jlpt-vocab-backup-${isoDay(today)}.json`;
  const file = new File([toBackup(db)], name, { type: 'application/json' });
  try {
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file] });
    } else {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(file);
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }
  } catch (e) {
    if (e.name !== 'AbortError') alert(`내보내기 실패: ${e.message}`);
    return;
  }
  db.settings.lastBackup = today;
  persist('settings');
  renderSettings();
}

async function importBackup(e) {
  const f = e.target.files[0];
  e.target.value = '';
  if (!f) return;
  const data = fromBackup(await f.text());
  if (!data) { alert('백업 파일 형식이 아닙니다. 기존 데이터는 그대로입니다.'); return; }
  if (!confirm(`지금 데이터를 백업 파일(진도 ${Object.keys(data.progress).length}개)로 덮어씁니다. 계속할까요?`)) return;
  db = data;
  persist('progress', 'edits', 'settings');
  show('home');
}

/* ---------- 시작 ---------- */

function wire() {
  for (const b of document.querySelectorAll('[data-home]')) {
    b.addEventListener('click', () => ($('skim').hidden ? show('home') : leaveSkim()));
  }
  $('startStudy').onclick = startStudy;
  $('startSkim').onclick = startSkim;
  $('openSettings').onclick = () => show('settings');

  $('skimYes').onclick = () => skim(true);
  $('skimNo').onclick = () => skim(false);
  $('skimUndo').onclick = undoSkim;
  let x0 = null;                 // 오른쪽 스와이프 = 안다, 왼쪽 = 모른다
  $('skimCard').addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  $('skimCard').addEventListener('touchend', (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    x0 = null;
    if (Math.abs(dx) > 60) skim(dx > 0);
  });

  $('studyCard').onclick = reveal;
  $('editKo').onclick = editKo;
  for (const b of $('gradeRow').children) b.onclick = () => answer(Number(b.dataset.g));

  $('examInput').onchange = changeSettings;
  $('bufferInput').onchange = changeSettings;
  $('exportBtn').onclick = exportBackup;
  $('importInput').onchange = importBackup;

  // 앱을 다시 열었을 때 날짜가 바뀌었으면 어느 화면이든 홈으로, 아니면 홈만 갱신
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    if (dayNum(new Date()) !== today) show('home');
    else if (!$('home').hidden) renderHome();
  });
}

async function init() {
  try {
    const res = await fetch('words.json');
    if (!res.ok) throw new Error(res.status);
    words = await res.json();
  } catch {
    $('todayLine').textContent = '단어 데이터를 불러오지 못했습니다. 인터넷에 연결해 한 번 열어 주세요.';
    return;
  }
  byKey = new Map(words.map((w) => [keyOf(w), w]));
  wire();
  show('home');
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
}

init();
