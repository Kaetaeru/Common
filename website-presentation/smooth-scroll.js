(() => {
  const legacyChapter = document.getElementById('legacy');
  if (!legacyChapter) return;

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const wheelGain = 10;
  const friction = 4.6;
  const maxVelocity = 3200;

  let position = window.scrollY;
  let velocity = 0;
  let frame = 0;
  let lastTime = 0;
  let legacyAccumulator = 0;
  let legacyLocked = false;
  let legacyResetTimer = 0;

  function maximumScroll() {
    return Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  }

  function legacyBounds() {
    const start = legacyChapter.offsetTop;
    const end = Math.max(start, start + legacyChapter.offsetHeight - window.innerHeight);
    return { start, end };
  }

  function isInsideLegacy(y = window.scrollY) {
    const { start, end } = legacyBounds();
    return y >= start - 1 && y <= end + 1;
  }

  function stopMomentum() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    lastTime = 0;
    velocity = 0;
    position = window.scrollY;
  }

  function startMomentum() {
    if (frame) return;
    position = window.scrollY;
    lastTime = performance.now();
    frame = requestAnimationFrame(tick);
  }

  function constrainLegacyCrossing(previousY, nextY) {
    const { start, end } = legacyBounds();
    if (previousY < start && nextY >= start) return start;
    if (previousY > end && nextY <= end) return end;
    return nextY;
  }

  function tick(now) {
    const dt = Math.min(Math.max((now - lastTime) / 1000, 0), 0.034);
    lastTime = now;

    const previousY = position;
    let nextY = position + velocity * dt;
    nextY = constrainLegacyCrossing(previousY, nextY);
    nextY = clamp(nextY, 0, maximumScroll());

    const hitBoundary = nextY !== position + velocity * dt;
    position = nextY;
    window.scrollTo(0, position);

    velocity *= Math.exp(-friction * dt);

    if (hitBoundary || Math.abs(velocity) < 6) {
      velocity = 0;
      position = window.scrollY;
      frame = 0;
      lastTime = 0;
      return;
    }

    frame = requestAnimationFrame(tick);
  }

  function addWheelImpulse(delta) {
    if (!frame) startMomentum();
    velocity = clamp(velocity + delta * wheelGain, -maxVelocity, maxVelocity);
  }

  function exitLegacy(direction) {
    stopMomentum();
    velocity = direction * 1100;
    startMomentum();
  }

  function legacyStep(direction) {
    const { start, end } = legacyBounds();
    const y = window.scrollY;

    if (direction < 0 && y <= start + 1) {
      exitLegacy(-1);
      return;
    }
    if (direction > 0 && y >= end - 1) {
      exitLegacy(1);
      return;
    }

    stopMomentum();
    const step = Math.max(120, window.innerHeight * 0.2);
    const next = clamp(y + step * direction, start, end);
    window.scrollTo(0, next);
    position = next;
  }

  function resetLegacyWheelSoon() {
    window.clearTimeout(legacyResetTimer);
    legacyResetTimer = window.setTimeout(() => {
      legacyAccumulator = 0;
      legacyLocked = false;
    }, 140);
  }

  window.addEventListener('wheel', (event) => {
    if (event.ctrlKey || event.metaKey) return;

    const target = event.target instanceof Element ? event.target : null;
    if (target?.closest('input, textarea, select')) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    const modeScale = event.deltaMode === 1 ? 28 : event.deltaMode === 2 ? window.innerHeight : 1;
    const normalized = clamp(event.deltaY * modeScale, -140, 140);
    if (!normalized) return;

    if (isInsideLegacy()) {
      stopMomentum();
      legacyAccumulator += normalized;

      if (!legacyLocked && Math.abs(legacyAccumulator) >= 28) {
        const direction = legacyAccumulator > 0 ? 1 : -1;
        legacyAccumulator = 0;
        legacyLocked = true;
        legacyStep(direction);
      }

      resetLegacyWheelSoon();
      return;
    }

    legacyAccumulator = 0;
    legacyLocked = false;
    addWheelImpulse(normalized);
  }, { passive: false, capture: true });

  window.addEventListener('mousedown', (event) => {
    if (event.button === 1) stopMomentum();
  }, { capture: true });

  window.addEventListener('scroll', () => {
    if (!frame) position = window.scrollY;
  }, { passive: true });

  window.addEventListener('resize', () => {
    stopMomentum();
    position = clamp(window.scrollY, 0, maximumScroll());
  });
})();
