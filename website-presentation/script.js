(() => {
  const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
  const mix = (a, b, t) => a + (b - a) * t;
  const smoothstep = (t) => t * t * (3 - 2 * t);
  const range = (value, start, end) => clamp((value - start) / (end - start));
  const rgb = (values) => `rgb(${values.map((v) => Math.round(v)).join(',')})`;
  const mixRgb = (a, b, t) => rgb(a.map((value, index) => mix(value, b[index], t)));

  const chapters = [...document.querySelectorAll('.chapter')];
  const progressFill = document.getElementById('progressFill');
  const slideNumber = document.getElementById('slideNumber');
  const slideLabel = document.getElementById('slideLabel');
  const prevButton = document.getElementById('prevButton');
  const nextButton = document.getElementById('nextButton');
  const restartButton = document.getElementById('restartButton');

  const introSoft = document.getElementById('introSoft');
  const introStrong = document.getElementById('introStrong');
  const introCopy = document.getElementById('introCopy');
  const introHint = document.getElementById('introHint');

  const productDemo = document.getElementById('productDemo');
  const styleName = document.getElementById('styleName');
  const styleCount = document.getElementById('styleCount');

  const deviceShell = document.getElementById('deviceShell');
  const deviceViewport = document.getElementById('deviceViewport');
  const deviceCamera = document.getElementById('deviceCamera');
  const deviceShadow = document.getElementById('deviceShadow');
  const devicePhaseLabel = document.getElementById('devicePhaseLabel');
  const legacyChapter = document.getElementById('legacy');
  const legacyWindow = document.getElementById('legacyWindow');

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const themes = [
    {
      name: 'EDITORIAL / LUXURY', bg: [238, 233, 222], fg: [22, 21, 18], accent: [166, 119, 68],
      copyX: 7, copyY: 24, copyW: 38, title: 64, tag: 64,
      lampX: 50, lampY: 5, lampW: 46, lampRot: -3, lampScale: 1,
      buyX: 7, buyY: 77, factsX: 56, factsY: 75, radius: 0, grid: 0
    },
    {
      name: 'SWISS / FUNCTIONAL', bg: [247, 245, 239], fg: [17, 17, 17], accent: [226, 58, 46],
      copyX: 4, copyY: 22, copyW: 44, title: 92, tag: 44,
      lampX: 61, lampY: 13, lampW: 34, lampRot: -7, lampScale: 1,
      buyX: 4, buyY: 80, factsX: 57, factsY: 73, radius: 0, grid: .45
    },
    {
      name: 'PLAYFUL / EXPRESSIVE', bg: [255, 98, 72], fg: [10, 43, 184], accent: [255, 235, 144],
      copyX: 5, copyY: 18, copyW: 57, title: 106, tag: 72,
      lampX: 59, lampY: 15, lampW: 44, lampRot: 11, lampScale: 1.08,
      buyX: 73, buyY: 77, factsX: 5, factsY: 80, radius: 28, grid: 0
    },
    {
      name: 'CINEMATIC / IMMERSIVE', bg: [15, 14, 13], fg: [238, 231, 219], accent: [255, 190, 92],
      copyX: 6, copyY: 57, copyW: 39, title: 42, tag: 78,
      lampX: 33, lampY: -5, lampW: 60, lampRot: 0, lampScale: 1.16,
      buyX: 77, buyY: 79, factsX: 6, factsY: 24, radius: 0, grid: 0
    }
  ];

  function chapterProgress(chapter, scrollY = window.scrollY) {
    const travel = Math.max(1, chapter.offsetHeight - window.innerHeight);
    return clamp((scrollY - chapter.offsetTop) / travel);
  }

  function activeChapter(scrollY = window.scrollY) {
    const marker = scrollY + window.innerHeight * .42;
    let current = chapters[0];
    chapters.forEach((chapter) => {
      if (chapter.offsetTop <= marker) current = chapter;
    });
    return current;
  }

  function renderFrame(scrollY) {
    const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    progressFill.style.width = `${clamp(scrollY / max) * 100}%`;
    const chapter = activeChapter(scrollY);
    const index = chapters.indexOf(chapter);
    slideNumber.textContent = `${String(index + 1).padStart(2, '0')} / 08`;
    slideLabel.textContent = chapter.dataset.label;
    prevButton.disabled = scrollY <= 2;
    nextButton.disabled = scrollY >= max - 2;
  }

  function renderIntro(scrollY) {
    const p = chapterProgress(document.getElementById('intro'), scrollY);
    const softP = smoothstep(range(p, .08, .58));
    const strongP = smoothstep(range(p, .2, .84));
    introSoft.style.transform = `translate3d(0, ${-softP * 70}px, 0)`;
    introSoft.style.opacity = String(1 - softP);
    introStrong.style.transform = `translate3d(0, ${-strongP * 28}px, 0)`;
    introCopy.style.transform = `scale(${1 - strongP * .045})`;
    introCopy.style.opacity = String(1 - smoothstep(range(p, .78, 1)) * .7);
    const hintP = smoothstep(range(p, .02, .32));
    introHint.style.opacity = String(1 - hintP);
    introHint.style.transform = `translate(-50%, ${hintP * 14}px)`;
  }

  function renderVisual(scrollY) {
    const chapter = document.getElementById('visual');
    const p = chapterProgress(chapter, scrollY);
    const position = clamp(p * 3, 0, 3);
    const base = Math.min(2, Math.floor(position));
    const next = Math.min(3, base + 1);
    const t = smoothstep(position - base);
    const a = themes[base];
    const b = themes[next];

    const setVar = (name, value) => productDemo.style.setProperty(name, value);
    setVar('--bg', mixRgb(a.bg, b.bg, t));
    setVar('--fg', mixRgb(a.fg, b.fg, t));
    setVar('--accent', mixRgb(a.accent, b.accent, t));
    setVar('--copy-x', mix(a.copyX, b.copyX, t));
    setVar('--copy-y', mix(a.copyY, b.copyY, t));
    setVar('--copy-w', mix(a.copyW, b.copyW, t));
    setVar('--title-size', mix(a.title, b.title, t));
    setVar('--tag-size', mix(a.tag, b.tag, t));
    setVar('--lamp-x', mix(a.lampX, b.lampX, t));
    setVar('--lamp-y', mix(a.lampY, b.lampY, t));
    setVar('--lamp-w', mix(a.lampW, b.lampW, t));
    setVar('--lamp-rot', mix(a.lampRot, b.lampRot, t));
    setVar('--lamp-scale', mix(a.lampScale, b.lampScale, t));
    setVar('--buy-x', mix(a.buyX, b.buyX, t));
    setVar('--buy-y', mix(a.buyY, b.buyY, t));
    setVar('--facts-x', mix(a.factsX, b.factsX, t));
    setVar('--facts-y', mix(a.factsY, b.factsY, t));
    setVar('--radius', mix(a.radius, b.radius, t));
    setVar('--grid-opacity', mix(a.grid, b.grid, t));

    const nearest = Math.min(3, Math.round(position));
    productDemo.dataset.theme = String(nearest);
    styleName.textContent = themes[nearest].name;
    styleCount.textContent = `STYLE ${String(nearest + 1).padStart(2, '0')} / 04`;

    const handoff = smoothstep(range(p, .9, 1));
    productDemo.style.transform = `scale(${1 - handoff * .045}) translateY(${-handoff * 12}px)`;
    productDemo.style.boxShadow = `0 ${30 + handoff * 20}px ${90 + handoff * 40}px rgba(0,0,0,${handoff * .22})`;
  }

  function deviceGeometry(type) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (type === 'phone') {
      return { w: Math.min(340, vw * .78), h: Math.min(680, vh * .78), r: 38, border: 8, cameraW: 72, cameraH: 18, shadow: 310 };
    }
    if (type === 'tablet') {
      return { w: Math.min(760, vw * .84), h: Math.min(580, vh * .72), r: 28, border: 9, cameraW: 9, cameraH: 9, shadow: 570 };
    }
    return { w: Math.min(980, vw * .64), h: Math.min(650, vh * .76), r: 8, border: 1, cameraW: 0, cameraH: 0, shadow: Math.min(620, vw * .5) };
  }

  function applyDeviceGeometry(a, b, t) {
    const e = smoothstep(t);
    deviceShell.style.width = `${mix(a.w, b.w, e)}px`;
    deviceShell.style.height = `${mix(a.h, b.h, e)}px`;
    deviceShell.style.borderRadius = `${mix(a.r, b.r, e)}px`;
    deviceShell.style.borderWidth = `${mix(a.border, b.border, e)}px`;
    deviceCamera.style.width = `${mix(a.cameraW, b.cameraW, e)}px`;
    deviceCamera.style.height = `${mix(a.cameraH, b.cameraH, e)}px`;
    deviceCamera.style.opacity = String(clamp(mix(a.cameraW ? 1 : 0, b.cameraW ? 1 : 0, e)));
    deviceShadow.style.width = `${mix(a.shadow, b.shadow, e)}px`;
  }

  function renderResponsive(scrollY) {
    const p = chapterProgress(document.getElementById('responsive'), scrollY);
    const desktop = deviceGeometry('desktop');
    const phone = deviceGeometry('phone');
    const tablet = deviceGeometry('tablet');

    let label = 'DESKTOP → PHONE';
    let relativeScroll = 0;

    if (p < .22) {
      applyDeviceGeometry(desktop, phone, range(p, 0, .22));
      relativeScroll = 0;
    } else if (p < .42) {
      applyDeviceGeometry(phone, phone, 1);
      relativeScroll = smoothstep(range(p, .22, .42)) * .92;
      label = 'PHONE / LIVE SCROLL';
    } else if (p < .68) {
      const t = range(p, .42, .68);
      applyDeviceGeometry(phone, tablet, t);
      relativeScroll = mix(.92, .16, smoothstep(t));
      label = 'PHONE → TABLET';
    } else if (p < .9) {
      applyDeviceGeometry(tablet, tablet, 1);
      relativeScroll = mix(.16, .96, smoothstep(range(p, .68, .9)));
      label = 'TABLET / LIVE SCROLL';
    } else {
      applyDeviceGeometry(tablet, tablet, 1);
      relativeScroll = .96;
      label = 'RESPONSIVE COMPLETE';
    }

    const maxScroll = Math.max(0, deviceViewport.scrollHeight - deviceViewport.clientHeight);
    deviceViewport.scrollTop = maxScroll * relativeScroll;
    devicePhaseLabel.textContent = label;

    const depth = smoothstep(range(p, .02, .2));
    deviceShell.style.transform = `translate3d(0, ${mix(28, 0, depth)}px, 0)`;
    deviceShadow.style.opacity = String(.55 + depth * .35);
  }

  function renderLegacy(scrollY) {
    const p = chapterProgress(legacyChapter, scrollY);
    const enter = range(p, 0, .22);
    const stepped = Math.round(enter * 5) / 5;
    legacyWindow.style.transform = `translateY(${(1 - stepped) * 28}px)`;
    legacyWindow.style.filter = enter < .12 ? 'brightness(1.18) contrast(.92)' : 'none';
  }

  let renderQueued = false;
  function render() {
    renderQueued = false;
    const y = window.scrollY;
    renderFrame(y);
    renderIntro(y);
    renderVisual(y);
    renderResponsive(y);
    renderLegacy(y);
  }

  function queueRender() {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(render);
  }

  let targetY = window.scrollY;
  let currentY = window.scrollY;
  let smoothActive = false;
  let smoothFrame = 0;
  let lastSmoothTime = 0;
  let legacyWheelAccumulator = 0;
  let legacyWheelLocked = false;
  let legacyWheelTimer = 0;

  function maximumScroll() {
    return Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  }

  function legacyBounds() {
    const start = legacyChapter.offsetTop;
    const end = Math.max(start, legacyChapter.offsetTop + legacyChapter.offsetHeight - window.innerHeight);
    return { start, end };
  }

  function isLegacyPosition(scrollY = window.scrollY) {
    const { start, end } = legacyBounds();
    return scrollY >= start - 1 && scrollY <= end + 1;
  }

  function stopSmoothScroll() {
    if (smoothFrame) cancelAnimationFrame(smoothFrame);
    smoothFrame = 0;
    smoothActive = false;
    lastSmoothTime = 0;
    currentY = window.scrollY;
    targetY = currentY;
  }

  function constrainToLegacyBoundary(from, to) {
    const { start, end } = legacyBounds();
    if (from < start && to > start) return start;
    if (from > end && to < end) return end;
    return to;
  }

  function animateSmoothScroll(now) {
    const deltaSeconds = lastSmoothTime ? Math.min((now - lastSmoothTime) / 1000, .05) : 1 / 60;
    lastSmoothTime = now;

    const distance = targetY - currentY;
    const follow = 1 - Math.exp(-6.2 * deltaSeconds);
    currentY += distance * follow;

    if (Math.abs(distance) < .35) currentY = targetY;

    window.scrollTo(0, currentY);
    queueRender();

    if (currentY !== targetY) {
      smoothFrame = requestAnimationFrame(animateSmoothScroll);
    } else {
      smoothActive = false;
      smoothFrame = 0;
      lastSmoothTime = 0;
    }
  }

  function moveTarget(delta) {
    const proposed = clamp(targetY + delta, 0, maximumScroll());
    targetY = constrainToLegacyBoundary(targetY, proposed);

    if (!smoothActive) {
      smoothActive = true;
      currentY = window.scrollY;
      lastSmoothTime = 0;
      if (smoothFrame) cancelAnimationFrame(smoothFrame);
      smoothFrame = requestAnimationFrame(animateSmoothScroll);
    }
  }

  function legacyStep(direction) {
    const { start, end } = legacyBounds();
    const y = window.scrollY;

    if ((direction < 0 && y <= start + 1) || (direction > 0 && y >= end - 1)) {
      currentY = y;
      targetY = y;
      moveTarget(window.innerHeight * .86 * direction);
      return;
    }

    stopSmoothScroll();
    const step = Math.max(120, window.innerHeight * .2);
    const next = clamp(y + step * direction, start, end);
    window.scrollTo(0, next);
    currentY = next;
    targetY = next;
    queueRender();
  }

  function resetLegacyWheelSoon() {
    window.clearTimeout(legacyWheelTimer);
    legacyWheelTimer = window.setTimeout(() => {
      legacyWheelAccumulator = 0;
      legacyWheelLocked = false;
    }, 150);
  }

  if (!reducedMotion) {
    window.addEventListener('wheel', (event) => {
      if (event.ctrlKey || event.metaKey) return;
      const editable = event.target.closest('input, textarea, select');
      if (editable) return;

      event.preventDefault();
      const modeScale = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1;
      const normalized = clamp(event.deltaY * modeScale, -220, 220);

      if (isLegacyPosition()) {
        stopSmoothScroll();
        legacyWheelAccumulator += normalized;

        if (!legacyWheelLocked && Math.abs(legacyWheelAccumulator) >= 36) {
          const direction = legacyWheelAccumulator > 0 ? 1 : -1;
          legacyWheelAccumulator = 0;
          legacyWheelLocked = true;
          legacyStep(direction);
        }

        resetLegacyWheelSoon();
        return;
      }

      legacyWheelAccumulator = 0;
      legacyWheelLocked = false;
      moveTarget(normalized * 1.22);
    }, { passive: false });
  }

  window.addEventListener('scroll', () => {
    if (!smoothActive) {
      currentY = window.scrollY;
      targetY = window.scrollY;
    }
    queueRender();
  }, { passive: true });

  window.addEventListener('resize', () => {
    targetY = clamp(targetY, 0, maximumScroll());
    currentY = window.scrollY;
    queueRender();
  });

  function nudge(direction) {
    if (isLegacyPosition()) {
      legacyStep(direction);
      return;
    }

    const delta = window.innerHeight * .86 * direction;
    if (reducedMotion) {
      window.scrollBy({ top: delta, behavior: 'auto' });
      return;
    }
    moveTarget(delta);
  }

  prevButton.addEventListener('click', () => nudge(-1));
  nextButton.addEventListener('click', () => nudge(1));

  document.addEventListener('keydown', (event) => {
    if (event.target.matches('input, textarea, select, button, a')) return;
    if (['ArrowDown', 'ArrowRight'].includes(event.key)) {
      event.preventDefault();
      nudge(1);
    } else if (['ArrowUp', 'ArrowLeft'].includes(event.key)) {
      event.preventDefault();
      nudge(-1);
    }
  });

  restartButton.addEventListener('click', () => {
    stopSmoothScroll();
    targetY = 0;
    if (reducedMotion) {
      window.scrollTo({ top: 0, behavior: 'auto' });
    } else {
      currentY = window.scrollY;
      moveTarget(-currentY);
    }
  });

  requestAnimationFrame(() => {
    currentY = window.scrollY;
    targetY = window.scrollY;
    render();
  });
})();