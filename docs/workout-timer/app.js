/* 운동 타이머 — 인터벌 / 라운드 / 세트 + 스톱워치 (오프라인 PWA) */
(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ------------------------------------------------------------------ 저장 */
  const KEY = { config: 'wt.config.v1', presets: 'wt.presets.v1', options: 'wt.options.v1' };

  const load = (key, fallback) => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (_) {
      return fallback;
    }
  };
  const save = (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* 사생활 보호 모드 등 */ }
  };

  /* ------------------------------------------------------------------ 설정 */
  const FIELDS = {
    prepare: { min: 0, max: 600, def: 10 },
    work:    { min: 1, max: 3600, def: 30 },
    rest:    { min: 0, max: 3600, def: 15 },
    rounds:  { min: 1, max: 99, def: 8 },
    sets:    { min: 1, max: 20, def: 1 },
    setRest: { min: 0, max: 3600, def: 60 },
  };

  const BUILT_IN = [
    { name: '타바타',     config: { prepare: 10, work: 20, rest: 10, rounds: 8, sets: 1, setRest: 60 } },
    { name: 'HIIT',       config: { prepare: 10, work: 40, rest: 20, rounds: 10, sets: 1, setRest: 60 } },
    { name: 'EMOM',       config: { prepare: 10, work: 60, rest: 0, rounds: 10, sets: 1, setRest: 60 } },
    { name: '근력 세트',  config: { prepare: 10, work: 45, rest: 90, rounds: 5, sets: 1, setRest: 120 } },
    { name: '복싱 3분',   config: { prepare: 10, work: 180, rest: 60, rounds: 3, sets: 1, setRest: 60 } },
    { name: '플랭크',     config: { prepare: 5, work: 60, rest: 0, rounds: 1, sets: 1, setRest: 60 } },
    { name: '스트레칭',   config: { prepare: 5, work: 30, rest: 5, rounds: 10, sets: 1, setRest: 60 } },
  ];

  const defaults = () => Object.fromEntries(Object.entries(FIELDS).map(([k, v]) => [k, v.def]));

  const clean = (raw) => {
    const out = defaults();
    for (const [key, rule] of Object.entries(FIELDS)) {
      const n = Math.round(Number(raw && raw[key]));
      if (Number.isFinite(n)) out[key] = Math.min(rule.max, Math.max(rule.min, n));
    }
    return out;
  };

  let config = clean(load(KEY.config, defaults()));
  let presets = load(KEY.presets, []);
  let options = Object.assign({ sound: true, vibe: true, awake: true }, load(KEY.options, {}));

  /* ------------------------------------------------------------------ 계획 */
  const PHASE = {
    prepare: { label: '준비', vibe: [80] },
    work:    { label: '운동', vibe: [120, 60, 120] },
    rest:    { label: '휴식', vibe: [80] },
    setRest: { label: '세트 휴식', vibe: [80, 60, 80] },
  };

  let plan = [];       // [{ type, dur, round, set }]
  let tailDur = [];    // plan[i] 이후에 남은 초
  let planTotal = 0;

  function buildPlan(c) {
    const list = [];
    if (c.prepare > 0) list.push({ type: 'prepare', dur: c.prepare, round: 1, set: 1 });
    for (let s = 1; s <= c.sets; s++) {
      for (let r = 1; r <= c.rounds; r++) {
        list.push({ type: 'work', dur: c.work, round: r, set: s });
        if (r < c.rounds && c.rest > 0) list.push({ type: 'rest', dur: c.rest, round: r, set: s });
      }
      if (s < c.sets && c.setRest > 0) list.push({ type: 'setRest', dur: c.setRest, round: c.rounds, set: s });
    }
    return list;
  }

  function refreshPlan() {
    plan = buildPlan(config);
    tailDur = new Array(plan.length).fill(0);
    let acc = 0;
    for (let i = plan.length - 1; i >= 0; i--) {
      tailDur[i] = acc;
      acc += plan[i].dur;
    }
    planTotal = acc;
  }

  /* ------------------------------------------------------------------ 소리 */
  let ctx = null;
  let scheduled = [];

  function audio() {
    if (!options.sound) return null;
    try {
      if (!ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        ctx = new AC();
      }
      if (ctx.state === 'suspended') ctx.resume();
      return ctx;
    } catch (_) {
      return null;
    }
  }

  function tone(at, freq, dur, vol) {
    const ac = audio();
    if (!ac) return;
    const when = Math.max(ac.currentTime, at);
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, when);
    gain.gain.exponentialRampToValueAtTime(vol, when + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, when + dur);
    osc.connect(gain).connect(ac.destination);
    osc.start(when);
    osc.stop(when + dur + 0.05);
    scheduled.push({ osc, at: when });
  }

  function cancelScheduled() {
    const ac = ctx;
    const now = ac ? ac.currentTime : 0;
    for (const item of scheduled) {
      if (item.at > now + 0.05) { try { item.osc.stop(0); } catch (_) {} }
    }
    scheduled = scheduled.filter((item) => item.at <= now + 0.05);
  }

  // 단계 시작 신호
  function cue(at, type) {
    if (type === 'work') { tone(at, 880, 0.16, 0.32); tone(at + 0.18, 1175, 0.22, 0.32); }
    else if (type === 'rest') tone(at, 660, 0.3, 0.26);
    else if (type === 'setRest') { tone(at, 520, 0.3, 0.26); tone(at + 0.34, 440, 0.34, 0.24); }
    else if (type === 'prepare') tone(at, 520, 0.2, 0.24);
    else if (type === 'done') { tone(at, 660, 0.18, 0.3); tone(at + 0.2, 880, 0.18, 0.3); tone(at + 0.4, 1320, 0.5, 0.32); }
  }

  // 현재 단계가 끝날 때까지의 카운트다운 + 전환 신호를 미리 예약한다.
  // (아이폰이 화면을 끄거나 앱을 내려도 예약된 소리는 그대로 울린다)
  function scheduleCues() {
    const ac = audio();
    if (!ac || !run.running) return;
    const remainMs = run.phaseEnd - Date.now();
    if (remainMs <= 0) return;
    const end = ac.currentTime + remainMs / 1000;
    for (const k of [3, 2, 1]) {
      if (remainMs > k * 1000 + 150) tone(end - k, 784, 0.1, 0.2);
    }
    const next = plan[run.idx + 1];
    if (next) cue(end, next.type);
    else for (let i = 0; i < 3; i++) cue(end + i * 3.6, 'done'); // 놓치지 않게 세 번
  }

  function buzz(type) {
    if (!options.vibe || !navigator.vibrate) return;
    const pattern = type === 'done' ? [200, 90, 200] : (PHASE[type] && PHASE[type].vibe) || [80];
    try { navigator.vibrate(pattern); } catch (_) {}
  }

  /* ------------------------------------------------------------- 화면 잠금 */
  let wakeLock = null;

  async function keepAwake(on) {
    try {
      if (!on || !('wakeLock' in navigator)) {
        if (wakeLock) { await wakeLock.release(); wakeLock = null; }
        return;
      }
      if (wakeLock) return;
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release', () => { wakeLock = null; });
    } catch (_) {
      wakeLock = null;
    }
  }

  /* ------------------------------------------------------------- 인터벌 실행 */
  const run = { running: false, started: false, done: false, idx: 0, phaseEnd: 0, pausedLeft: 0 };
  let raf = 0;
  let beat = 0;

  const el = {
    app: $('#app'),
    stage: $('#stage'),
    ring: $('#ringFg'),
    phase: $('#phaseLabel'),
    clock: $('#clock'),
    counter: $('#counter'),
    metaElapsed: $('#metaElapsed'),
    metaLeft: $('#metaLeft'),
    start: $('#btnStart'),
    skip: $('#btnSkip'),
    reset: $('#btnReset'),
    presets: $('#presets'),
    summary: $('#planSummary'),
    rowTimer: $('#controls-timer'),
    rowDone: $('#controls-done'),
    rowWorkout: $('#controls-workout'),
    picker: $('#picker'),
    pickerList: $('#pickerList'),
  };

  function showRow(which) {
    el.rowTimer.hidden = which !== 'timer';
    el.rowDone.hidden = which !== 'done';
    el.rowWorkout.hidden = which !== 'workout';
  }

  const RING = 2 * Math.PI * 90;

  function pad(n) { return String(n).padStart(2, '0'); }

  function fmt(totalSeconds) {
    const s = Math.max(0, Math.round(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return h > 0 ? `${h}:${pad(m)}:${pad(s % 60)}` : `${pad(m)}:${pad(s % 60)}`;
  }

  function startLoop() {
    stopLoop();
    const step = () => { tick(); raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
    // 탭이 뒤로 가면 rAF가 멈추므로 타이머로도 한 번 더 확인한다.
    beat = setInterval(tick, 500);
  }

  function stopLoop() {
    if (raf) cancelAnimationFrame(raf);
    if (beat) clearInterval(beat);
    raf = 0;
    beat = 0;
  }

  function begin() {
    refreshPlan();
    if (!plan.length) return;
    workout.active = false;
    closePicker();
    run.running = true;
    run.started = true;
    run.done = false;
    run.idx = 0;
    run.phaseEnd = Date.now() + plan[0].dur * 1000;
    cancelScheduled();
    const ac = audio();
    if (ac) cue(ac.currentTime, plan[0].type);
    buzz(plan[0].type);
    scheduleCues();
    keepAwake(options.awake);
    startLoop();
    render();
  }

  function pause() {
    if (!run.running) return;
    run.running = false;
    run.pausedLeft = Math.max(0, run.phaseEnd - Date.now());
    cancelScheduled();
    stopLoop();
    keepAwake(false);
    render();
  }

  function resume() {
    if (run.running || !run.started || run.done) return;
    run.running = true;
    run.phaseEnd = Date.now() + run.pausedLeft;
    scheduleCues();
    keepAwake(options.awake);
    startLoop();
    render();
  }

  function skip() {
    if (!run.started || run.done) return;
    cancelScheduled();
    run.idx += 1;
    if (run.idx >= plan.length) { finish(); return; }
    const dur = plan[run.idx].dur * 1000;
    if (run.running) {
      run.phaseEnd = Date.now() + dur;
      const ac = audio();
      if (ac) cue(ac.currentTime, plan[run.idx].type);
      buzz(plan[run.idx].type);
      scheduleCues();
    } else {
      run.pausedLeft = dur;
    }
    render();
  }

  function reset() {
    cancelScheduled();
    stopLoop();
    keepAwake(false);
    workout.active = false;
    run.running = false;
    run.started = false;
    run.done = false;
    run.idx = 0;
    run.phaseEnd = 0;
    run.pausedLeft = 0;
    refreshPlan();
    render();
  }

  function finish() {
    stopLoop();
    keepAwake(false);
    run.running = false;
    run.done = true;
    run.idx = plan.length;
    buzz('done');
    render();
  }

  function tick() {
    if (workout.active) { renderWorkout(); return; }
    if (!run.running) return;
    const now = Date.now();
    let jumped = 0;
    while (run.idx < plan.length && now >= run.phaseEnd) {
      run.idx += 1;
      jumped += 1;
      if (run.idx < plan.length) run.phaseEnd += plan[run.idx].dur * 1000;
    }
    if (run.idx >= plan.length) { finish(); return; }
    if (jumped) {
      buzz(plan[run.idx].type);
      if (jumped > 1) { cancelScheduled(); }      // 백그라운드에서 여러 단계를 지나친 경우
      scheduleCues();
    }
    render();
  }

  function render() {
    const total = planTotal;

    if (workout.active) { renderWorkout(); return; }

    if (!run.started) {
      showRow('timer');
      el.stage.dataset.phase = 'idle';
      el.stage.classList.remove('is-paused');
      el.app.classList.remove('is-focus');
      el.phase.textContent = '준비 완료';
      el.clock.textContent = fmt(plan.length ? plan[0].dur : 0);
      el.counter.textContent = `${config.rounds}라운드 · ${config.sets}세트`;
      el.ring.style.strokeDashoffset = 0;
      el.metaElapsed.textContent = '경과 00:00';
      el.metaLeft.textContent = `전체 ${fmt(total)}`;
      el.start.textContent = '시작';
      el.skip.disabled = true;
      return;
    }

    if (run.done) {
      showRow('done');
      el.stage.dataset.phase = 'done';
      el.stage.classList.remove('is-paused');
      el.app.classList.add('is-focus');
      el.phase.textContent = '완료';
      el.clock.textContent = fmt(total);
      el.counter.textContent = workout.sets ? `${workout.sets}세트 완료` : `${config.rounds}라운드 × ${config.sets}세트 끝`;
      el.ring.style.strokeDashoffset = 0;
      el.metaElapsed.textContent = `경과 ${fmt(total)}`;
      el.metaLeft.textContent = '운동 시작을 누르세요';
      el.skip.disabled = true;
      return;
    }

    const item = plan[run.idx];
    const leftMs = run.running ? Math.max(0, run.phaseEnd - Date.now()) : run.pausedLeft;
    const leftSec = leftMs / 1000;
    const ratio = item.dur > 0 ? Math.min(1, Math.max(0, leftSec / item.dur)) : 0;

    showRow('timer');
    el.stage.dataset.phase = item.type;
    el.stage.classList.toggle('is-paused', !run.running);
    el.app.classList.toggle('is-focus', run.running);
    el.phase.textContent = PHASE[item.type].label + (run.running ? '' : ' (일시정지)');
    el.clock.textContent = fmt(Math.ceil(leftSec));
    el.ring.style.strokeDashoffset = RING * (1 - ratio);

    const parts = [];
    if (config.rounds > 1) parts.push(`라운드 ${item.round}/${config.rounds}`);
    if (config.sets > 1) parts.push(`세트 ${item.set}/${config.sets}`);
    if (workout.sets > 0) parts.push(`${workout.sets}세트 완료`);
    if (!parts.length) parts.push(`총 ${fmt(total)}`);
    el.counter.textContent = parts.join(' · ');

    const remainAll = leftSec + tailDur[run.idx];
    el.metaElapsed.textContent = `경과 ${fmt(total - remainAll)}`;
    el.metaLeft.textContent = `남음 ${fmt(remainAll)}`;
    el.start.textContent = run.running ? '일시정지' : '계속';
    el.skip.disabled = false;
  }

  /* --------------------------------------------------------- 운동모드 */
  // 타이머가 끝나면 '운동 시작'을 눌러 운동모드로 들어간다. 운동모드는 시간을
  // 세면서 두 가지 끝내기를 준다.
  //   운동모드 종료 → 다음 타이머(같은 휴식)를 바로 이어서 시작
  //   세트 종료     → 타이머 선택창으로
  const workout = { active: false, startedAt: 0, sets: 0 };

  function enterWorkout() {
    cancelScheduled();
    stopLoop();
    run.started = false;
    run.running = false;
    run.done = false;
    workout.active = true;
    workout.startedAt = Date.now();
    const ac = audio();
    if (ac) cue(ac.currentTime, 'work');
    buzz('work');
    keepAwake(options.awake);
    startLoop();
    renderWorkout();
  }

  function leaveWorkout() {
    workout.sets += 1;
    workout.active = false;
    stopLoop();
    keepAwake(false);
  }

  function nextTimer() {
    if (!workout.active) return;
    leaveWorkout();
    begin();
  }

  function endSet() {
    if (!workout.active) return;
    leaveWorkout();
    reset();
    openPicker();
  }

  function renderWorkout() {
    const sec = (Date.now() - workout.startedAt) / 1000;
    showRow('workout');
    el.app.classList.add('is-focus');
    el.stage.dataset.phase = 'workout';
    el.stage.classList.remove('is-paused');
    el.phase.textContent = '운동 중';
    el.clock.textContent = fmt(sec);
    el.counter.textContent = `${workout.sets + 1}번째 세트`;
    el.ring.style.strokeDashoffset = 0;
    el.metaElapsed.textContent = workout.sets ? `완료 ${workout.sets}세트` : '세트 진행 중';
    el.metaLeft.textContent = `다음 타이머 ${fmt(planTotal)}`;
  }

  /* ---------------------------------------------------- 타이머 선택창 */
  const planLength = (c) => buildPlan(c).reduce((sum, step) => sum + step.dur, 0);

  function openPicker() {
    cancelScheduled();
    renderPicker();
    el.picker.hidden = false;
    el.app.classList.add('is-picking');
    window.scrollTo(0, 0);
  }

  function closePicker() {
    el.picker.hidden = true;
    el.app.classList.remove('is-picking');
  }

  function renderPicker() {
    el.pickerList.innerHTML = '';
    for (const item of BUILT_IN.concat(presets)) {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'pick';
      const left = document.createElement('span');
      const name = document.createElement('b');
      name.textContent = item.name;
      const detail = document.createElement('small');
      detail.textContent = ' ' + describe(item.config);
      left.append(name, detail);
      const total = document.createElement('span');
      total.className = 'total';
      total.textContent = fmt(planLength(item.config));
      row.append(left, total);
      row.addEventListener('click', () => {
        workout.sets = 0;            // 새 운동을 고른 것이므로 세트 수를 새로 센다
        applyPreset(item.config);
        closePicker();
        begin();
      });
      el.pickerList.append(row);
    }
  }

  function toggleStart() {
    if (workout.active) return;
    if (run.done) { enterWorkout(); return; }
    if (!run.started) begin();
    else if (run.running) pause();
    else resume();
  }

  $('#btnWorkout').addEventListener('click', enterWorkout);
  $('#btnAgain').addEventListener('click', () => { cancelScheduled(); workout.sets = 0; begin(); });
  $('#btnPick').addEventListener('click', () => { reset(); openPicker(); });
  $('#btnNextTimer').addEventListener('click', nextTimer);
  $('#btnEndSet').addEventListener('click', endSet);
  $('#pickerClose').addEventListener('click', () => { closePicker(); render(); });

  el.start.addEventListener('click', toggleStart);
  $('#dial').addEventListener('click', toggleStart);
  el.skip.addEventListener('click', skip);
  el.reset.addEventListener('click', reset);

  /* ---------------------------------------------------------- 설정 입력 UI */
  const inputs = Object.fromEntries(Object.keys(FIELDS).map((k) => [k, $('#f-' + k)]));

  function setField(key, value) {
    const rule = FIELDS[key];
    config[key] = Math.min(rule.max, Math.max(rule.min, Math.round(value)));
    inputs[key].value = config[key];
    afterConfigChange();
  }

  function afterConfigChange() {
    save(KEY.config, config);
    refreshPlan();
    $('#field-setRest').classList.toggle('is-off', config.sets < 2);
    el.summary.textContent = `${fmt(planTotal)} · ${plan.length}단계`;
    markActivePreset();
    if (!run.started) render();
  }

  for (const [key, input] of Object.entries(inputs)) {
    input.value = config[key];
    input.addEventListener('input', () => {
      const n = Number(input.value.replace(/[^0-9]/g, ''));
      if (input.value === '') return;
      config[key] = Number.isFinite(n) ? n : FIELDS[key].def;
      afterConfigChange();
    });
    input.addEventListener('blur', () => setField(key, Number(input.value) || FIELDS[key].min));
    input.addEventListener('focus', () => input.select());
  }

  $$('.step').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      const key = btn.closest('.field').dataset.key;
      setField(key, (Number(inputs[key].value) || 0) + Number(btn.dataset.delta));
    });
  });

  /* ------------------------------------------------------------- 프리셋 UI */
  const sameConfig = (a, b) => Object.keys(FIELDS).every((k) => a[k] === b[k]);

  function markActivePreset() {
    $$('.preset', el.presets).forEach((chip) => {
      const source = chip.dataset.kind === 'user' ? presets : BUILT_IN;
      const item = source[Number(chip.dataset.index)];
      chip.classList.toggle('is-on', !!item && sameConfig(item.config, config));
    });
  }

  function describe(c) {
    const round = c.rest > 0 ? `${c.work}/${c.rest}초` : `${c.work}초`;
    return `${round} × ${c.rounds}` + (c.sets > 1 ? ` × ${c.sets}세트` : '');
  }

  function applyPreset(c) {
    config = clean(c);
    for (const [key, input] of Object.entries(inputs)) input.value = config[key];
    reset();
    afterConfigChange();
  }

  function renderPresets() {
    el.presets.innerHTML = '';
    const add = (item, kind, index) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'preset';
      chip.dataset.kind = kind;
      chip.dataset.index = index;
      const name = document.createElement('span');
      name.textContent = item.name;
      const detail = document.createElement('small');
      detail.textContent = describe(item.config);
      chip.append(name, detail);
      chip.addEventListener('click', () => applyPreset(item.config));
      if (kind === 'user') {
        const del = document.createElement('span');
        del.className = 'x';
        del.textContent = '×';
        del.setAttribute('role', 'button');
        del.setAttribute('aria-label', `${item.name} 삭제`);
        del.addEventListener('click', (event) => {
          event.stopPropagation();
          if (!confirm(`'${item.name}' 프리셋을 지울까요?`)) return;
          presets.splice(index, 1);
          save(KEY.presets, presets);
          renderPresets();
        });
        chip.append(del);
      }
      el.presets.append(chip);
    };
    BUILT_IN.forEach((item, i) => add(item, 'built', i));
    presets.forEach((item, i) => add(item, 'user', i));
    markActivePreset();
  }

  $('#btnSavePreset').addEventListener('click', () => {
    const name = (prompt('프리셋 이름', describe(config)) || '').trim();
    if (!name) return;
    const existing = presets.findIndex((p) => p.name === name);
    const entry = { name, config: Object.assign({}, config) };
    if (existing >= 0) presets[existing] = entry; else presets.push(entry);
    save(KEY.presets, presets);
    renderPresets();
  });

  /* ---------------------------------------------------------------- 옵션 */
  const optSound = $('#optSound');
  const optVibe = $('#optVibe');
  const optAwake = $('#optAwake');
  optSound.checked = options.sound;
  optVibe.checked = options.vibe;
  optAwake.checked = options.awake;

  optSound.addEventListener('change', () => {
    options.sound = optSound.checked;
    save(KEY.options, options);
    if (!options.sound) cancelScheduled();
    else if (run.running) scheduleCues();
  });
  optVibe.addEventListener('change', () => { options.vibe = optVibe.checked; save(KEY.options, options); });
  optAwake.addEventListener('change', () => {
    options.awake = optAwake.checked;
    save(KEY.options, options);
    keepAwake(options.awake && run.running);
  });

  /* ------------------------------------------------------------- 스톱워치 */
  const sw = { running: false, base: 0, elapsed: 0, laps: [] };
  const swEl = { clock: $('#swClock'), counter: $('#swCounter'), laps: $('#swLaps'), start: $('#swStart'), lap: $('#swLap'), reset: $('#swReset') };
  let swTimer = 0;

  const swNow = () => sw.elapsed + (sw.running ? Date.now() - sw.base : 0);

  function fmtMs(ms) {
    const s = Math.floor(ms / 1000);
    const tenth = Math.floor((ms % 1000) / 100);
    const h = Math.floor(s / 3600);
    const head = h > 0 ? `${h}:${pad(Math.floor((s % 3600) / 60))}` : pad(Math.floor((s % 3600) / 60));
    return `${head}:${pad(s % 60)}.${tenth}`;
  }

  function swRender() {
    swEl.clock.textContent = fmtMs(swNow());
    swEl.counter.textContent = `랩 ${sw.laps.length}개`;
    swEl.start.textContent = sw.running ? '정지' : (sw.elapsed > 0 ? '계속' : '시작');
    swEl.lap.disabled = !sw.running;
  }

  function swPaint() {
    swEl.laps.innerHTML = '';
    sw.laps.forEach((lap, i) => {
      const li = document.createElement('li');
      const left = document.createElement('span');
      left.textContent = `랩 ${i + 1}`;
      const right = document.createElement('span');
      right.textContent = `${fmtMs(lap.split)}  (${fmtMs(lap.total)})`;
      li.append(left, right);
      swEl.laps.prepend(li);
    });
  }

  swEl.start.addEventListener('click', () => {
    if (sw.running) {
      sw.elapsed = swNow();
      sw.running = false;
      clearInterval(swTimer);
      keepAwake(false);
    } else {
      sw.base = Date.now();
      sw.running = true;
      swTimer = setInterval(swRender, 100);
      keepAwake(options.awake);
    }
    swRender();
  });

  swEl.lap.addEventListener('click', () => {
    if (!sw.running) return;
    const total = swNow();
    const prev = sw.laps.length ? sw.laps[sw.laps.length - 1].total : 0;
    sw.laps.push({ total, split: total - prev });
    swPaint();
    swRender();
  });

  swEl.reset.addEventListener('click', () => {
    clearInterval(swTimer);
    sw.running = false;
    sw.elapsed = 0;
    sw.laps = [];
    keepAwake(false);
    swPaint();
    swRender();
  });

  /* ------------------------------------------------------------------ 탭 */
  $$('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      $$('.tab').forEach((other) => {
        const on = other === tab;
        other.classList.toggle('is-on', on);
        other.setAttribute('aria-selected', String(on));
      });
      $('#panel-interval').hidden = tab.dataset.tab !== 'interval';
      $('#panel-stopwatch').hidden = tab.dataset.tab !== 'stopwatch';
      window.scrollTo(0, 0);
    });
  });

  /* -------------------------------------------------- 백그라운드 복귀 처리 */
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    if (run.running) {
      if (ctx && ctx.state === 'suspended') ctx.resume();
      keepAwake(options.awake);
      tick();
    }
    if (workout.active) {
      if (ctx && ctx.state === 'suspended') ctx.resume();
      keepAwake(options.awake);
      renderWorkout();
    }
    if (sw.running) swRender();
  });

  /* ---------------------------------------------------------------- 시작 */
  renderPresets();
  afterConfigChange();
  reset();
  swPaint();
  swRender();

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => { /* file:// 로 열면 무시 */ });
    });
  }
})();
