/* 운동 타이머 — 세트(운동 수동 · 휴식 타이머) / 인터벌 / 스톱워치 (오프라인 PWA) */
(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ------------------------------------------------------------------ 저장 */
  const KEY = {
    config: 'wt.config.v1',
    presets: 'wt.presets.v1',
    options: 'wt.options.v1',
    rest: 'wt.rest.v1',
    install: 'wt.install.hidden.v1',
  };

  const load = (key, fallback) => {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (_) {
      return fallback;
    }
  };
  const save = (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* 사생활 보호 모드 등 */ }
  };

  const clamp = (n, min, max) => Math.min(max, Math.max(min, n));
  const pad = (n) => String(n).padStart(2, '0');

  function fmt(totalSeconds) {
    const s = Math.max(0, Math.round(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return h > 0 ? `${h}:${pad(m)}:${pad(s % 60)}` : `${pad(m)}:${pad(s % 60)}`;
  }

  const app = $('#app');
  const RING = 2 * Math.PI * 90;

  let options = Object.assign(
    { sound: true, vibe: true, awake: true, background: false },
    load(KEY.options, {})
  );

  /* ------------------------------------------------------------------ 소리 */
  const PHASE = {
    prepare: { label: '준비', vibe: [80] },
    work:    { label: '운동', vibe: [120, 60, 120] },
    rest:    { label: '휴식', vibe: [80] },
    setRest: { label: '세트 휴식', vibe: [80, 60, 80] },
  };

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
    const now = ctx ? ctx.currentTime : 0;
    for (const item of scheduled) {
      if (item.at > now + 0.05) { try { item.osc.stop(0); } catch (_) {} }
    }
    scheduled = scheduled.filter((item) => item.at <= now + 0.05);
  }

  function cue(at, type) {
    if (type === 'work') { tone(at, 880, 0.16, 0.32); tone(at + 0.18, 1175, 0.22, 0.32); }
    else if (type === 'rest') tone(at, 660, 0.3, 0.26);
    else if (type === 'setRest') { tone(at, 520, 0.3, 0.26); tone(at + 0.34, 440, 0.34, 0.24); }
    else if (type === 'prepare') tone(at, 520, 0.2, 0.24);
    else if (type === 'done') { tone(at, 660, 0.18, 0.3); tone(at + 0.2, 880, 0.18, 0.3); tone(at + 0.4, 1320, 0.5, 0.32); }
  }

  function cueNow(type) {
    const ac = audio();
    if (ac) cue(ac.currentTime, type);
  }

  // 남은 시간이 끝날 때까지의 카운트다운과 끝 신호를 미리 예약한다.
  // 예약해 두면 화면이 꺼져 있어도 그대로 울린다.
  function scheduleCountdown(untilMs, endType) {
    const ac = audio();
    if (!ac) return;
    const remain = untilMs - Date.now();
    if (remain <= 0) return;
    const end = ac.currentTime + remain / 1000;
    for (const k of [3, 2, 1]) {
      if (remain > k * 1000 + 150) tone(end - k, 784, 0.1, 0.2);
    }
    if (endType === 'done') for (let i = 0; i < 3; i++) cue(end + i * 3.6, 'done'); // 놓치지 않게 세 번
    else cue(end, endType);
  }

  function buzz(type) {
    if (!options.vibe || !navigator.vibrate) return;
    const pattern = type === 'done' ? [200, 90, 200] : (PHASE[type] && PHASE[type].vibe) || [80];
    try { navigator.vibrate(pattern); } catch (_) {}
  }

  /* -------------------------------------------- 백그라운드 유지용 오디오 */
  // 아이폰은 화면을 잠그거나 앱을 내리면 페이지를 멈춘다. 들리지 않는 소리를
  // 계속 재생하면 오디오 세션이 살아 있어 타이머와 예약된 알람이 그대로 돈다.
  // 대신 다른 앱의 음악이 끊길 수 있어 기본값은 꺼 둔다.
  let keeper = null;

  function keeperSource() {
    const rate = 8000;
    const frames = rate;                      // 1초를 반복 재생
    const buf = new ArrayBuffer(44 + frames * 2);
    const view = new DataView(buf);
    const tag = (at, text) => { for (let i = 0; i < text.length; i++) view.setUint8(at + i, text.charCodeAt(i)); };
    tag(0, 'RIFF'); view.setUint32(4, 36 + frames * 2, true); tag(8, 'WAVEfmt ');
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    tag(36, 'data'); view.setUint32(40, frames * 2, true);
    for (let i = 0; i < frames; i++) view.setInt16(44 + i * 2, i % 2 ? 1 : -1, true); // 최소 진폭 = 들리지 않음
    return URL.createObjectURL(new Blob([buf], { type: 'audio/wav' }));
  }

  function holdAudio(on) {
    const want = on && options.background && options.sound;
    try {
      if (!want) {
        if (keeper) keeper.pause();
        return;
      }
      if (!keeper) {
        keeper = new Audio(keeperSource());
        keeper.loop = true;
        keeper.setAttribute('playsinline', '');
        keeper.hidden = true;
        document.body.append(keeper);   // 문서에 붙은 미디어라야 사파리가 계속 재생한다
        if ('mediaSession' in navigator) {
          // 잠금화면 재생 컨트롤을 타이머에 연결한다. 전화 같은 방해로 소리가
          // 끊긴 경우가 아니라, 직접 누른 경우에만 불린다.
          try {
            navigator.mediaSession.setActionHandler('pause', () => lockScreenPause());
            navigator.mediaSession.setActionHandler('play', () => lockScreenPlay());
          } catch (_) {}
        }
      }
      if ('audioSession' in navigator) navigator.audioSession.type = 'playback';
      const played = keeper.play();
      if (played && played.catch) played.catch(() => {});
    } catch (_) { /* 오디오를 못 쓰는 브라우저 */ }
  }

  let nowPlaying = '';

  function setNowPlaying(text, playing) {
    if (!('mediaSession' in navigator) || !keeper || keeper.paused) return;
    try {
      navigator.mediaSession.playbackState = playing ? 'playing' : 'paused';
      if (text === nowPlaying) return;
      nowPlaying = text;
      navigator.mediaSession.metadata = new window.MediaMetadata({
        title: text,
        artist: '운동 타이머',
        artwork: [{ src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' }],
      });
    } catch (_) {}
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

  /* ---------------------------------------------------------------- 루프 */
  let raf = 0;
  let beat = 0;
  let ticker = null;

  function startLoop(fn) {
    stopLoop();
    ticker = fn;
    const step = () => { if (ticker) ticker(); raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
    beat = setInterval(() => { if (ticker) ticker(); }, 500);  // 탭이 뒤로 가면 rAF가 멈춘다
  }

  function stopLoop() {
    if (raf) cancelAnimationFrame(raf);
    if (beat) clearInterval(beat);
    raf = 0;
    beat = 0;
    ticker = null;
  }

  /* ================================================================ 세트 */
  // 운동 시간은 정하지 않는다. 운동하는 동안은 시간이 올라가고, 직접 눌러 끝낸다.
  //   운동 중 → [휴식 시작] → 휴식 카운트다운 → 알람 → [운동 시작] → 다음 세트
  //   [세트 끝] → 타이머 완전 종료
  const REST = { min: 5, max: 3600, def: 90 };
  let restSec = clamp(Math.round(Number(load(KEY.rest, REST.def))) || REST.def, REST.min, REST.max);

  const set = { phase: 'idle', from: 0, restEnd: 0, sets: 0, startedAt: 0, endedAt: 0, done: false };

  const sEl = {
    stage: $('#setStage'),
    ring: $('#setRing'),
    phase: $('#setPhase'),
    clock: $('#setClock'),
    counter: $('#setCounter'),
    metaA: $('#setMetaA'),
    metaB: $('#setMetaB'),
    rowIdle: $('#setRowIdle'),
    rowWork: $('#setRowWork'),
    rowRest: $('#setRowRest'),
    input: $('#f-restOnly'),
    chips: $('#restChips'),
  };

  function setSessionSeconds() {
    if (!set.startedAt) return 0;
    const until = set.phase === 'idle' ? (set.endedAt || set.startedAt) : Date.now();
    return (until - set.startedAt) / 1000;
  }

  function startWork() {
    cancelScheduled();
    if (set.phase === 'idle') {
      set.sets = 0;
      set.startedAt = Date.now();
      set.endedAt = 0;
      set.done = false;
    }
    set.sets += 1;
    set.phase = 'work';
    set.from = Date.now();
    cueNow('work');
    buzz('work');
    keepAwake(options.awake);
    holdAudio(true);
    startLoop(setTick);
    setRender();
  }

  function startRest() {
    if (set.phase !== 'work') return;
    cancelScheduled();
    set.phase = 'rest';
    set.from = Date.now();
    set.restEnd = Date.now() + restSec * 1000;
    cueNow('rest');
    buzz('rest');
    scheduleCountdown(set.restEnd, 'done');
    keepAwake(options.awake);
    holdAudio(true);
    startLoop(setTick);
    setRender();
  }

  function endSet() {
    if (set.phase === 'idle') return;
    cancelScheduled();
    stopLoop();
    keepAwake(false);
    holdAudio(false);
    set.endedAt = Date.now();
    set.phase = 'idle';
    set.done = true;
    setRender();
  }

  function setTick() {
    if (set.phase === 'rest' && Date.now() >= set.restEnd) {
      set.phase = 'ready';
      set.from = set.restEnd;
      buzz('done');
    }
    setRender();
  }

  function setRender() {
    const phase = set.phase;
    sEl.rowIdle.hidden = phase !== 'idle';
    sEl.rowWork.hidden = phase !== 'work';
    sEl.rowRest.hidden = phase !== 'rest' && phase !== 'ready';
    app.classList.toggle('is-focus', phase !== 'idle');

    sEl.metaA.textContent = `세트 ${set.sets}`;
    sEl.metaB.textContent = `총 ${fmt(setSessionSeconds())}`;

    if (phase === 'idle') {
      sEl.stage.dataset.phase = set.done ? 'done' : 'idle';
      sEl.phase.textContent = set.done ? '세트 끝' : '준비';
      sEl.clock.textContent = set.done ? fmt(setSessionSeconds()) : fmt(restSec);
      sEl.counter.textContent = set.done
        ? `${set.sets}세트 완료`
        : `휴식 ${fmt(restSec)} · 운동 시작을 누르세요`;
      sEl.ring.style.strokeDashoffset = 0;
      return;
    }

    if (phase === 'work') {
      const sec = (Date.now() - set.from) / 1000;
      sEl.stage.dataset.phase = 'work';
      sEl.phase.textContent = '운동 중';
      sEl.clock.textContent = fmt(sec);
      sEl.counter.textContent = `${set.sets}번째 세트`;
      sEl.ring.style.strokeDashoffset = 0;
      setNowPlaying(`운동 중 · ${set.sets}번째 세트`, true);
      return;
    }

    if (phase === 'rest') {
      const left = Math.max(0, set.restEnd - Date.now()) / 1000;
      sEl.stage.dataset.phase = 'rest';
      sEl.phase.textContent = '휴식';
      sEl.clock.textContent = fmt(Math.ceil(left));
      sEl.counter.textContent = `${set.sets}세트 완료`;
      sEl.ring.style.strokeDashoffset = RING * (1 - clamp(left / restSec, 0, 1));
      setNowPlaying(`휴식 ${fmt(Math.ceil(left))}`, true);
      return;
    }

    const over = (Date.now() - set.from) / 1000;   // ready
    sEl.stage.dataset.phase = 'ready';
    sEl.phase.textContent = '휴식 끝';
    sEl.clock.textContent = fmt(over);
    sEl.counter.textContent = '운동 시작을 누르세요';
    sEl.ring.style.strokeDashoffset = 0;
    setNowPlaying('휴식 끝 · 운동 시작', true);
  }

  function lockScreenPause() {
    if (set.phase === 'work') startRest();
    else if (run.running) intervalPause();
  }

  function lockScreenPlay() {
    if (set.phase === 'rest' || set.phase === 'ready') startWork();
    else if (run.started && !run.running) intervalResume();
  }

  $('#setGoWork').addEventListener('click', startWork);
  $('#setGoWork2').addEventListener('click', startWork);
  $('#setGoRest').addEventListener('click', startRest);
  $$('.set-end').forEach((btn) => btn.addEventListener('click', endSet));
  $('#setDial').addEventListener('click', () => {
    if (set.phase === 'work') startRest();
    else startWork();                              // idle · rest · ready
  });

  function setRest(value) {
    restSec = clamp(Math.round(value) || REST.min, REST.min, REST.max);
    sEl.input.value = restSec;
    save(KEY.rest, restSec);
    $$('.chip', sEl.chips).forEach((chip) => {
      chip.classList.toggle('is-on', Number(chip.dataset.sec) === restSec);
    });
    if (set.phase === 'idle') setRender();
  }

  sEl.input.value = restSec;
  sEl.input.addEventListener('input', () => {
    if (sEl.input.value === '') return;
    const n = Number(sEl.input.value.replace(/[^0-9]/g, ''));
    if (Number.isFinite(n)) setRest(n);
  });
  sEl.input.addEventListener('blur', () => setRest(Number(sEl.input.value) || REST.def));
  sEl.input.addEventListener('focus', () => sEl.input.select());

  $$('.step', $('#restField')).forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      setRest((Number(sEl.input.value) || 0) + Number(btn.dataset.delta));
    });
  });

  for (const sec of [30, 45, 60, 90, 120, 180]) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip';
    chip.dataset.sec = sec;
    chip.textContent = sec < 60 ? `${sec}초` : `${sec / 60}분`;
    chip.addEventListener('click', () => setRest(sec));
    sEl.chips.append(chip);
  }

  /* ============================================================== 인터벌 */
  const FIELDS = {
    prepare: { min: 0, max: 600, def: 10 },
    work:    { min: 1, max: 3600, def: 30 },
    rest:    { min: 0, max: 3600, def: 15 },
    rounds:  { min: 1, max: 99, def: 8 },
    sets:    { min: 1, max: 20, def: 1 },
    setRest: { min: 0, max: 3600, def: 60 },
  };

  const BUILT_IN = [
    { name: '타바타',    config: { prepare: 10, work: 20, rest: 10, rounds: 8, sets: 1, setRest: 60 } },
    { name: 'HIIT',      config: { prepare: 10, work: 40, rest: 20, rounds: 10, sets: 1, setRest: 60 } },
    { name: 'EMOM',      config: { prepare: 10, work: 60, rest: 0, rounds: 10, sets: 1, setRest: 60 } },
    { name: '근력 세트', config: { prepare: 10, work: 45, rest: 90, rounds: 5, sets: 1, setRest: 120 } },
    { name: '복싱 3분',  config: { prepare: 10, work: 180, rest: 60, rounds: 3, sets: 1, setRest: 60 } },
    { name: '플랭크',    config: { prepare: 5, work: 60, rest: 0, rounds: 1, sets: 1, setRest: 60 } },
    { name: '스트레칭',  config: { prepare: 5, work: 30, rest: 5, rounds: 10, sets: 1, setRest: 60 } },
  ];

  const defaults = () => Object.fromEntries(Object.entries(FIELDS).map(([k, v]) => [k, v.def]));

  const clean = (raw) => {
    const out = defaults();
    for (const [key, rule] of Object.entries(FIELDS)) {
      const n = Math.round(Number(raw && raw[key]));
      if (Number.isFinite(n)) out[key] = clamp(n, rule.min, rule.max);
    }
    return out;
  };

  let config = clean(load(KEY.config, defaults()));
  let presets = load(KEY.presets, []);

  let plan = [];
  let tailDur = [];
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

  const run = { running: false, started: false, done: false, idx: 0, phaseEnd: 0, pausedLeft: 0 };

  const el = {
    stage: $('#stage'),
    ring: $('#ringFg'),
    phase: $('#phaseLabel'),
    clock: $('#clock'),
    counter: $('#counter'),
    metaElapsed: $('#metaElapsed'),
    metaLeft: $('#metaLeft'),
    start: $('#btnStart'),
    skip: $('#btnSkip'),
    presets: $('#presets'),
    summary: $('#planSummary'),
  };

  function scheduleIntervalCues() {
    if (!run.running) return;
    const next = plan[run.idx + 1];
    scheduleCountdown(run.phaseEnd, next ? next.type : 'done');
  }

  function intervalBegin() {
    refreshPlan();
    if (!plan.length) return;
    run.running = true;
    run.started = true;
    run.done = false;
    run.idx = 0;
    run.phaseEnd = Date.now() + plan[0].dur * 1000;
    cancelScheduled();
    cueNow(plan[0].type);
    buzz(plan[0].type);
    scheduleIntervalCues();
    keepAwake(options.awake);
    holdAudio(true);
    startLoop(intervalTick);
    intervalRender();
  }

  function intervalPause() {
    if (!run.running) return;
    run.running = false;
    run.pausedLeft = Math.max(0, run.phaseEnd - Date.now());
    cancelScheduled();
    stopLoop();
    keepAwake(false);
    holdAudio(false);
    intervalRender();
  }

  function intervalResume() {
    if (run.running || !run.started || run.done) return;
    run.running = true;
    run.phaseEnd = Date.now() + run.pausedLeft;
    scheduleIntervalCues();
    keepAwake(options.awake);
    holdAudio(true);
    startLoop(intervalTick);
    intervalRender();
  }

  function intervalSkip() {
    if (!run.started || run.done) return;
    cancelScheduled();
    run.idx += 1;
    if (run.idx >= plan.length) { intervalFinish(); return; }
    const dur = plan[run.idx].dur * 1000;
    if (run.running) {
      run.phaseEnd = Date.now() + dur;
      cueNow(plan[run.idx].type);
      buzz(plan[run.idx].type);
      scheduleIntervalCues();
    } else {
      run.pausedLeft = dur;
    }
    intervalRender();
  }

  function intervalReset() {
    cancelScheduled();
    stopLoop();
    keepAwake(false);
    holdAudio(false);
    run.running = false;
    run.started = false;
    run.done = false;
    run.idx = 0;
    run.phaseEnd = 0;
    run.pausedLeft = 0;
    refreshPlan();
    intervalRender();
  }

  function intervalFinish() {
    stopLoop();
    keepAwake(false);
    run.running = false;
    run.done = true;
    run.idx = plan.length;
    buzz('done');
    intervalRender();
  }

  function intervalTick() {
    if (!run.running) return;
    const now = Date.now();
    let jumped = 0;
    while (run.idx < plan.length && now >= run.phaseEnd) {
      run.idx += 1;
      jumped += 1;
      if (run.idx < plan.length) run.phaseEnd += plan[run.idx].dur * 1000;
    }
    if (run.idx >= plan.length) { intervalFinish(); return; }
    if (jumped) {
      buzz(plan[run.idx].type);
      if (jumped > 1) cancelScheduled();        // 백그라운드에서 여러 단계를 지나친 경우
      scheduleIntervalCues();
    }
    intervalRender();
  }

  function intervalRender() {
    const total = planTotal;

    if (!run.started) {
      el.stage.dataset.phase = 'idle';
      el.stage.classList.remove('is-paused');
      app.classList.remove('is-focus');
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
      el.stage.dataset.phase = 'done';
      el.stage.classList.remove('is-paused');
      app.classList.remove('is-focus');
      el.phase.textContent = '완료';
      el.clock.textContent = fmt(total);
      el.counter.textContent = `${config.rounds}라운드 × ${config.sets}세트 끝`;
      el.ring.style.strokeDashoffset = 0;
      el.metaElapsed.textContent = `경과 ${fmt(total)}`;
      el.metaLeft.textContent = '수고했어요';
      el.start.textContent = '다시 시작';
      el.skip.disabled = true;
      setNowPlaying('완료', false);
      return;
    }

    const item = plan[run.idx];
    const leftMs = run.running ? Math.max(0, run.phaseEnd - Date.now()) : run.pausedLeft;
    const leftSec = leftMs / 1000;

    el.stage.dataset.phase = item.type;
    el.stage.classList.toggle('is-paused', !run.running);
    app.classList.toggle('is-focus', run.running);
    el.phase.textContent = PHASE[item.type].label + (run.running ? '' : ' (일시정지)');
    el.clock.textContent = fmt(Math.ceil(leftSec));
    el.ring.style.strokeDashoffset = RING * (1 - (item.dur > 0 ? clamp(leftSec / item.dur, 0, 1) : 0));

    const parts = [`라운드 ${item.round}/${config.rounds}`];
    if (config.sets > 1) parts.push(`세트 ${item.set}/${config.sets}`);
    el.counter.textContent = parts.join(' · ');

    const remainAll = leftSec + tailDur[run.idx];
    el.metaElapsed.textContent = `경과 ${fmt(total - remainAll)}`;
    el.metaLeft.textContent = `남음 ${fmt(remainAll)}`;
    el.start.textContent = run.running ? '일시정지' : '계속';
    el.skip.disabled = false;
    setNowPlaying(`${PHASE[item.type].label} ${fmt(Math.ceil(leftSec))}`, run.running);
  }

  function intervalToggle() {
    if (run.done || !run.started) intervalBegin();
    else if (run.running) intervalPause();
    else intervalResume();
  }

  el.start.addEventListener('click', intervalToggle);
  $('#dial').addEventListener('click', intervalToggle);
  el.skip.addEventListener('click', intervalSkip);
  $('#btnReset').addEventListener('click', intervalReset);

  /* ------------------------------------------------------ 인터벌 설정 UI */
  const inputs = Object.fromEntries(Object.keys(FIELDS).map((k) => [k, $('#f-' + k)]));

  function setField(key, value) {
    config[key] = clamp(Math.round(value), FIELDS[key].min, FIELDS[key].max);
    inputs[key].value = config[key];
    afterConfigChange();
  }

  function afterConfigChange() {
    save(KEY.config, config);
    refreshPlan();
    $('#field-setRest').classList.toggle('is-off', config.sets < 2);
    el.summary.textContent = `${fmt(planTotal)} · ${plan.length}단계`;
    markActivePreset();
    if (!run.started) intervalRender();
  }

  for (const [key, input] of Object.entries(inputs)) {
    input.value = config[key];
    input.addEventListener('input', () => {
      if (input.value === '') return;
      const n = Number(input.value.replace(/[^0-9]/g, ''));
      config[key] = Number.isFinite(n) ? n : FIELDS[key].def;
      afterConfigChange();
    });
    input.addEventListener('blur', () => setField(key, Number(input.value) || FIELDS[key].min));
    input.addEventListener('focus', () => input.select());
  }

  $$('.step', $('#fields')).forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      const key = btn.closest('.field').dataset.key;
      setField(key, (Number(inputs[key].value) || 0) + Number(btn.dataset.delta));
    });
  });

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
    intervalReset();
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
  const optBackground = $('#optBackground');
  optSound.checked = options.sound;
  optVibe.checked = options.vibe;
  optAwake.checked = options.awake;
  optBackground.checked = options.background;

  const timerLive = () => set.phase !== 'idle' || run.running;

  optSound.addEventListener('change', () => {
    options.sound = optSound.checked;
    save(KEY.options, options);
    if (!options.sound) { cancelScheduled(); holdAudio(false); }
    else {
      if (run.running) scheduleIntervalCues();
      if (set.phase === 'rest') scheduleCountdown(set.restEnd, 'done');
      holdAudio(timerLive());
    }
  });

  optVibe.addEventListener('change', () => { options.vibe = optVibe.checked; save(KEY.options, options); });

  optAwake.addEventListener('change', () => {
    options.awake = optAwake.checked;
    save(KEY.options, options);
    keepAwake(options.awake && timerLive());
  });

  optBackground.addEventListener('change', () => {
    options.background = optBackground.checked;
    save(KEY.options, options);
    holdAudio(timerLive());
  });

  /* ------------------------------------------------------------- 스톱워치 */
  const sw = { running: false, base: 0, elapsed: 0, laps: [] };
  const swEl = {
    clock: $('#swClock'), counter: $('#swCounter'), laps: $('#swLaps'),
    start: $('#swStart'), lap: $('#swLap'), reset: $('#swReset'),
  };
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
      $('#panel-set').hidden = tab.dataset.tab !== 'set';
      $('#panel-interval').hidden = tab.dataset.tab !== 'interval';
      $('#panel-stopwatch').hidden = tab.dataset.tab !== 'stopwatch';
      window.scrollTo(0, 0);
    });
  });

  /* -------------------------------------------------- 백그라운드 복귀 처리 */
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    if (timerLive()) {
      if (ctx && ctx.state === 'suspended') ctx.resume();
      keepAwake(options.awake);
      holdAudio(true);
    }
    if (set.phase !== 'idle') setTick();
    if (run.running) intervalTick();
    if (sw.running) swRender();
  });

  /* --------------------------------------------------------- 홈 화면 추가 */
  const standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  let installPrompt = null;

  function showInstallHint() {
    if (standalone) { app.classList.add('is-standalone'); return; }
    if (load(KEY.install, false)) return;
    $('#installText').innerHTML = isIOS
      ? '<b>홈 화면에 추가하면 앱처럼 열립니다.</b> 사파리 아래 공유 버튼 → 홈 화면에 추가'
      : '<b>홈 화면에 추가하면 앱처럼 열립니다.</b> 브라우저 메뉴에서 설치 또는 홈 화면에 추가';
    $('#install').hidden = false;
  }

  $('#installClose').addEventListener('click', () => {
    $('#install').hidden = true;
    save(KEY.install, true);
  });

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    installPrompt = event;
    $('#installGo').hidden = false;
  });

  $('#installGo').addEventListener('click', async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    $('#install').hidden = true;
  });

  /* ---------------------------------------------------------------- 시작 */
  showInstallHint();
  setRest(restSec);
  setRender();
  renderPresets();
  afterConfigChange();
  intervalReset();
  swPaint();
  swRender();

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => { /* file:// 로 열면 무시 */ });
    });
  }
})();
