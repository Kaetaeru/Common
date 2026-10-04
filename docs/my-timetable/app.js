(() => {
  'use strict';
  const T = window.TT;
  const C = T.calendar;
  const $ = (id) => document.getElementById(id);
  const WD = ['일', '월', '화', '수', '목', '금', '토'];
  const PIN = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 14.5s5-4.6 5-8.6A5 5 0 0 0 3 5.9c0 4 5 8.6 5 8.6z"/><circle cx="8" cy="6" r="1.8"/></svg>';

  /* ---------- 날짜 도구 (모두 일본 시간 기준, 'YYYY-MM-DD' 문자열) ---------- */
  const pad = (n) => String(n).padStart(2, '0');
  const parse = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(Date.UTC(y, m - 1, d)); };
  const fmt = (dt) => `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}`;
  const addDays = (s, n) => { const d = parse(s); d.setUTCDate(d.getUTCDate() + n); return fmt(d); };
  const dow = (s) => parse(s).getUTCDay();
  const diffDays = (a, b) => Math.round((parse(b) - parse(a)) / 864e5);
  const inRange = (s, [a, b]) => s >= a && s <= b;
  const toMin = (hm) => { const [h, m] = hm.split(':').map(Number); return h * 60 + m; };
  const nowJST = () => {
    const d = new Date(Date.now() + 9 * 3600e3);
    return { date: fmt(d), min: d.getUTCHours() * 60 + d.getUTCMinutes() };
  };
  const mondayOf = (s) => addDays(s, -((dow(s) + 6) % 7));
  const label = (s) => { const d = parse(s); return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 ${WD[d.getUTCDay()]}요일`; };
  const short = (s) => { const d = parse(s); return `${d.getUTCMonth() + 1}/${d.getUTCDate()}(${WD[d.getUTCDay()]})`; };
  const syllabus = (code) => `https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/${T.courses[code].sid}/2026${code}?language=en_US`;

  /* ---------- 그날 무슨 날인지, 어떤 수업이 있는지 ---------- */
  function dayInfo(s) {
    const wd = dow(s);
    const brk = C.breaks.find((b) => inRange(s, b));
    if (s < C.q1[0]) return { kind: 'pre', note: `개강 전입니다. 1쿼터 수업은 ${short(C.q1[0])}에 시작해요.`, slots: [] };
    if (brk) return { kind: 'break', note: `${brk[2]} (${short(brk[0])} ~ ${short(brk[1])})`, slots: [] };
    if (inRange(s, C.q1Exam)) return { kind: 'exam', note: '1쿼터 기말시험 기간입니다. 시험 시간과 장소는 수업별 공지를 확인하세요.', slots: [] };
    if (inRange(s, C.q2Exam)) return { kind: 'exam', note: '2쿼터 기말시험 기간입니다. 시험 시간과 장소는 수업별 공지를 확인하세요.', slots: [] };
    if (s > C.q2Exam[1]) return { kind: 'end', note: '가을학기가 끝났습니다.', slots: [] };
    if (C.makeupDays.includes(s)) return { kind: 'makeup', note: '보강일입니다. 보강 공지가 있는 수업만 열리고, 3교시부터 시간이 달라요 (3교시 13:05 시작).', slots: [] };
    if (wd === 0 || wd === 6) return { kind: 'weekend', note: '', slots: [] };
    const q = inRange(s, C.q1) ? 1 : inRange(s, C.q2) ? 2 : 0;
    if (!q) return { kind: 'gap', note: '쿼터 사이라 정규 수업이 없습니다.', slots: [] };
    const slots = T.slots
      .filter(([d, , code]) => d === wd && T.courses[code].term !== (q === 1 ? 'Q2' : 'Q1'))
      .sort((a, b) => a[1] - b[1]);
    let note = '';
    if (C.holidaysWithClass[s]) note = `${C.holidaysWithClass[s]}(공휴일)이지만 정상 수업일이에요.`;
    else if (q === 2 && T.slots.some(([d, , c]) => d === wd && T.courses[c].term === 'Q1')) note = '2쿼터부터는 1쿼터 과목(Negotiation Skills)이 빠집니다.';
    return { kind: 'class', q, note, slots };
  }

  function termLabel(s) {
    if (s < C.q1[0]) return `${T.term} · 개강 전`;
    if (s <= C.q1[1]) return `${T.term} · 1쿼터 ${Math.floor(diffDays(C.q1[0], s) / 7) + 1}주차`;
    if (s <= C.q1Exam[1]) return `${T.term} · 1쿼터 시험 기간`;
    if (s < C.q2[0]) return `${T.term} · 쿼터 사이`;
    if (inRange(s, C.q2Exam)) return `${T.term} · 2쿼터 시험 기간`;
    const brk = C.breaks.find((b) => inRange(s, b));
    if (brk) return `${T.term} · ${brk[2]}`;
    if (s <= C.q2Exam[1]) {
      const w = Math.floor(diffDays(C.q2[0], s) / 7) + 1;
      return `${T.term} · 2쿼터 ${w}주차`;
    }
    return `${T.term} · 종료`;
  }

  // 지금 이후 가장 가까운 수업 (오늘 남은 수업 포함)
  function nextClass(from, afterMin) {
    for (let i = 0; i < 160; i++) {
      const s = addDays(from, i);
      const hit = dayInfo(s).slots.find(([, p]) => i > 0 || toMin(T.periods[p][0]) > afterMin);
      if (hit) return { date: s, slot: hit };
    }
    return null;
  }

  /* ---------- 상태 ---------- */
  let view = 'day';
  let sel = nowJST().date;
  let followToday = true;

  /* ---------- 렌더링 ---------- */
  function renderTop() {
    const today = nowJST().date;
    $('termLabel').textContent = termLabel(sel);
    const m0 = mondayOf(sel);
    $('dateTitle').textContent = view === 'week' ? `${short(m0)} – ${short(addDays(m0, 4))}` : label(sel);
    $('goToday').hidden = sel === today;
    const mon = mondayOf(sel);
    let h = '';
    for (let i = 0; i < 7; i++) {
      const s = addDays(mon, i);
      const info = dayInfo(s);
      const n = info.slots.length;
      const cls = [s === today ? 'is-today' : '', n ? '' : 'is-off'].join(' ');
      h += `<button type="button" role="tab" class="${cls}" data-date="${s}" aria-selected="${s === sel}" aria-label="${label(s)}, 수업 ${n}개">
        <span class="wd">${WD[dow(s)]}</span><span class="dn">${parse(s).getUTCDate()}</span>
        <span class="dots">${'<i></i>'.repeat(Math.min(n, 4))}</span></button>`;
    }
    $('strip').innerHTML = h;
    $('jumpDate').value = sel;
  }

  function renderStatus() {
    const { date: today, min } = nowJST();
    const box = $('status');
    if (sel !== today) { box.hidden = true; return; }
    const info = dayInfo(today);
    const live = info.slots.find(([, p]) => min >= toMin(T.periods[p][0]) && min < toMin(T.periods[p][1]));
    const left = (x) => (x >= 60 ? `${Math.floor(x / 60)}시간 ${x % 60}분` : `${x}분`);
    box.hidden = false;
    if (live) {
      const [, p, code] = live;
      const [a, b] = T.periods[p];
      const pct = Math.round(((min - toMin(a)) / (toMin(b) - toMin(a))) * 100);
      const nx = nextClass(today, min);
      const nxToday = nx && nx.date === today ? ` · 다음 ${T.periods[nx.slot[1]][0]} ${T.courses[nx.slot[2]].room}` : '';
      box.className = 'status live';
      box.innerHTML = `<span class="dot"></span><div class="txt" style="flex:1">
        <span class="lbl">수업 중 · ${left(toMin(b) - min)} 남음</span>
        <span class="main">${T.courses[code].name}</span>
        <span class="meta"><b>${T.courses[code].room}</b> · ${a}–${b}${nxToday}</span>
        <div class="bar"><i style="width:${pct}%"></i></div></div>`;
      return;
    }
    const nx = nextClass(today, min);
    if (!nx) { box.hidden = true; return; }
    const [, p, code] = nx.slot;
    const c = T.courses[code];
    if (nx.date === today) {
      const until = toMin(T.periods[p][0]) - min;
      box.className = 'status next';
      box.innerHTML = `<span class="dot"></span><div class="txt">
        <span class="lbl">다음 수업 · ${left(until)} 후</span>
        <span class="main">${c.name}</span>
        <span class="meta"><b>${c.room}</b> · ${p}교시 ${T.periods[p].join('–')}</span></div>`;
    } else {
      const done = info.slots.length > 0;
      const when = nx.date === addDays(today, 1) ? '내일' : short(nx.date);
      box.className = 'status';
      box.innerHTML = `<span class="dot"></span><div class="txt">
        <span class="lbl">${done ? '오늘 수업 끝' : '오늘은 수업 없음'}</span>
        <span class="main">${when} ${T.periods[p][0]} · ${c.name}</span>
        <span class="meta"><b>${c.room}</b> · ${p}교시</span></div>`;
    }
  }

  function renderDay() {
    const { date: today, min } = nowJST();
    const info = dayInfo(sel);
    $('notice').hidden = !info.note;
    $('notice').textContent = info.note;
    const list = $('list');
    if (!info.slots.length) {
      const msg = { weekend: '주말이에요', break: '방학이에요', exam: '정규 수업 없음', makeup: '정해진 수업 없음', pre: '아직 개강 전', end: '학기 종료', gap: '정규 수업 없음' }[info.kind] || '수업 없음';
      list.innerHTML = `<li class="empty"><strong>${msg}</strong><span>${sel === today ? '' : label(sel)}</span></li>`;
      return;
    }
    let h = '';
    let prevEnd = null;
    info.slots.forEach(([, p, code]) => {
      const c = T.courses[code];
      const [a, b] = T.periods[p];
      if (prevEnd && toMin(a) - toMin(prevEnd) > 10) {
        const gap = toMin(a) - toMin(prevEnd);
        h += `<li class="item" aria-hidden="true"><span></span><span class="gap">${p === 3 ? '점심' : '공강'} ${prevEnd}–${a}${gap > 60 ? ` · ${Math.floor(gap / 60)}시간${gap % 60 ? ` ${gap % 60}분` : ''}` : ''}</span></li>`;
      }
      let st = '';
      if (sel === today) {
        if (min >= toMin(a) && min < toMin(b)) st = 'live';
        else if (min >= toMin(b)) st = 'done';
      } else if (sel < today) st = 'done';
      h += `<li class="item ${st}">
        <div class="time"><b>${a}</b><span>${b}</span></div>
        <div class="card">
          <div class="card-top"><div class="cname">${c.name}<small>${c.ko}</small></div><span class="room">${PIN}${c.room}</span></div>
          <div class="cmeta"><span class="period">${p}교시</span><span>${c.teacher}</span><a href="${syllabus(code)}" target="_blank" rel="noopener">#${code} 실라버스</a></div>
        </div></li>`;
      prevEnd = b;
    });
    list.innerHTML = h;
  }

  function renderWeek() {
    const { date: today, min } = nowJST();
    const mon = mondayOf(sel);
    const days = [0, 1, 2, 3, 4].map((i) => addDays(mon, i));
    const infos = days.map(dayInfo);
    const maxP = Math.max(4, ...T.slots.map((s) => s[1]));
    let h = '<thead><tr><th class="p"></th>';
    days.forEach((s) => { h += `<th class="${s === today ? 'is-today' : ''}">${WD[dow(s)]} ${parse(s).getUTCDate()}</th>`; });
    h += '</tr></thead><tbody>';
    for (let p = 1; p <= maxP; p++) {
      h += `<tr><th class="p"><b>${p}</b>${T.periods[p][0]}</th>`;
      days.forEach((s, i) => {
        const info = infos[i];
        const hit = info.slots.find((x) => x[1] === p);
        if (hit) {
          const c = T.courses[hit[2]];
          const live = s === today && min >= toMin(T.periods[p][0]) && min < toMin(T.periods[p][1]);
          h += `<td class="${live ? 'live' : ''}"><button type="button" data-date="${s}"><b>${c.short || c.name}</b><span>${c.room}</span></button></td>`;
        } else {
          h += `<td class="${info.kind === 'class' ? '' : 'off'}"></td>`;
        }
      });
      h += '</tr>';
    }
    $('grid').innerHTML = h + '</tbody>';
  }

  function renderCourses() {
    const order = [...new Set(T.slots.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]).map((s) => s[2]))];
    $('courses').innerHTML = order.map((code) => {
      const c = T.courses[code];
      const meets = T.slots.filter((s) => s[2] === code).map(([d, p]) => `<span>${WD[d]} ${p}교시 · ${T.periods[p][0]}</span>`).join('');
      return `<li class="card">
        <div class="card-top"><div class="cname">${c.name}<span class="tag">${c.term === 'Q1' ? '1쿼터' : '학기'}</span><small>${c.ko}</small></div><span class="room">${PIN}${c.room}</span></div>
        <div class="meet">${meets}</div>
        <div class="cmeta"><span>${c.teacher}</span><a href="${syllabus(code)}" target="_blank" rel="noopener">#${code} 실라버스</a></div>
      </li>`;
    }).join('');
  }

  function render() {
    renderTop();
    if (view === 'day') { renderStatus(); renderDay(); }
    if (view === 'week') renderWeek();
  }

  /* ---------- 조작 ---------- */
  function go(s, dir) {
    if (!s || s === sel) return;
    sel = s;
    followToday = sel === nowJST().date;
    const m = $('main');
    m.classList.remove('slide-l', 'slide-r');
    void m.offsetWidth;
    if (dir) m.classList.add(dir > 0 ? 'slide-l' : 'slide-r');
    render();
  }
  function setView(v) {
    view = v;
    document.querySelectorAll('.tab').forEach((t) => {
      const on = t.dataset.view === v;
      t.classList.toggle('is-on', on);
      t.setAttribute('aria-selected', on);
    });
    ['day', 'week', 'courses'].forEach((k) => { $('view-' + k).hidden = k !== v; });
    if (v === 'courses') renderCourses();
    render();
    window.scrollTo(0, 0);
  }

  $('prevDay').addEventListener('click', () => go(addDays(sel, view === 'week' ? -7 : -1), -1));
  $('nextDay').addEventListener('click', () => go(addDays(sel, view === 'week' ? 7 : 1), 1));
  $('goToday').addEventListener('click', () => go(nowJST().date, nowJST().date > sel ? 1 : -1));
  $('strip').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-date]');
    if (b) go(b.dataset.date, b.dataset.date > sel ? 1 : -1);
  });
  $('grid').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-date]');
    if (b) { sel = b.dataset.date; followToday = sel === nowJST().date; setView('day'); }
  });
  $('jumpDate').addEventListener('change', (e) => { if (e.target.value) go(e.target.value, e.target.value > sel ? 1 : -1); });
  document.querySelectorAll('.tab').forEach((t) => t.addEventListener('click', () => setView(t.dataset.view)));

  // 좌우로 밀어서 날짜 이동
  let sx = 0, sy = 0, st = 0;
  const main = $('main');
  main.addEventListener('touchstart', (e) => { const t = e.touches[0]; sx = t.clientX; sy = t.clientY; st = Date.now(); }, { passive: true });
  main.addEventListener('touchend', (e) => {
    if (view === 'courses') return;
    const t = e.changedTouches[0];
    const dx = t.clientX - sx, dy = t.clientY - sy;
    if (Math.abs(dx) > 60 && Math.abs(dy) < 45 && Date.now() - st < 600) {
      const step = view === 'week' ? 7 : 1;
      go(addDays(sel, dx < 0 ? step : -step), dx < 0 ? 1 : -1);
    }
  }, { passive: true });

  // 시간이 흐르면 상태 갱신, 날이 바뀌면 오늘로
  function tick() {
    const today = nowJST().date;
    if (followToday && sel !== today) sel = today;
    render();
  }
  setInterval(tick, 30000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) tick(); });

  render();

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
  }
})();
