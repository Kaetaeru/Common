(() => {
  const chapters = [...document.querySelectorAll('.chapter')];
  const legacyChapter = document.getElementById('legacy');
  const prevButton = document.getElementById('prevButton');
  const nextButton = document.getElementById('nextButton');
  const restartButton = document.getElementById('restartButton');
  if (!chapters.length || !legacyChapter) return;

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const wheelThreshold = 32;
  const gestureIdleMs = 180;

  let checkpoints = [];
  let animating = false;
  let animationFrame = 0;
  let wheelAccumulator = 0;
  let wheelDirection = 0;
  let gestureConsumed = false;
  let gestureResetTimer = 0;

  function chapterY(chapter, progress = 0) {
    const travel = Math.max(0, chapter.offsetHeight - window.innerHeight);
    return chapter.offsetTop + travel * progress;
  }

  function addCheckpoint(list, chapterId, progress, name) {
    const chapter = document.getElementById(chapterId);
    if (!chapter) return;
    list.push({ y: chapterY(chapter, progress), chapterId, name });
  }

  function rebuildCheckpoints() {
    const list = [];

    addCheckpoint(list, 'intro', 0, 'intro');

    addCheckpoint(list, 'visual', 0, 'visual-1');
    addCheckpoint(list, 'visual', 1 / 3, 'visual-2');
    addCheckpoint(list, 'visual', 2 / 3, 'visual-3');
    addCheckpoint(list, 'visual', 1, 'visual-4');

    addCheckpoint(list, 'responsive', 0, 'responsive-desktop');
    addCheckpoint(list, 'responsive', 0.22, 'responsive-phone');
    addCheckpoint(list, 'responsive', 0.42, 'responsive-phone-scroll');
    addCheckpoint(list, 'responsive', 0.68, 'responsive-tablet');
    addCheckpoint(list, 'responsive', 0.9, 'responsive-tablet-scroll');
    addCheckpoint(list, 'responsive', 1, 'responsive-complete');

    addCheckpoint(list, 'interaction', 0, 'interaction');
    addCheckpoint(list, 'legacy', 0, 'legacy');
    addCheckpoint(list, 'functional', 0, 'functional');
    addCheckpoint(list, 'data', 0, 'data');
    addCheckpoint(list, 'close', 0, 'close');

    const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    checkpoints = list
      .map((checkpoint) => ({ ...checkpoint, y: clamp(checkpoint.y, 0, maxScroll) }))
      .sort((a, b) => a.y - b.y)
      .filter((checkpoint, index, all) => index === 0 || Math.abs(checkpoint.y - all[index - 1].y) > 2);
  }

  function legacyBounds() {
    const start = legacyChapter.offsetTop;
    const end = Math.max(start, start + legacyChapter.offsetHeight - window.innerHeight);
    return { start, end };
  }

  function insideLegacy(y) {
    const { start, end } = legacyBounds();
    return y >= start - 2 && y <= end + 2;
  }

  function nextCheckpointIndex(direction, y = window.scrollY) {
    if (!checkpoints.length) return -1;

    if (direction > 0) {
      const index = checkpoints.findIndex((checkpoint) => checkpoint.y > y + 4);
      return index === -1 ? checkpoints.length - 1 : index;
    }

    for (let index = checkpoints.length - 1; index >= 0; index -= 1) {
      if (checkpoints[index].y < y - 4) return index;
    }
    return 0;
  }

  function stopAnimation() {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    animating = false;
  }

  function smoothEase(t) {
    return 1 - Math.pow(1 - t, 4);
  }

  function steppedEase(t) {
    const steps = 6;
    if (t >= 1) return 1;
    return Math.floor(t * steps) / steps;
  }

  function animateTo(targetY, mode = 'smooth') {
    stopAnimation();

    const startY = window.scrollY;
    const distance = Math.abs(targetY - startY);
    if (distance < 2) {
      window.scrollTo(0, targetY);
      return;
    }

    const legacy = mode === 'legacy';
    const duration = reducedMotion
      ? 120
      : legacy
        ? 430
        : clamp(680 + distance * 0.12, 760, 1180);
    const ease = legacy ? steppedEase : smoothEase;
    const startedAt = performance.now();
    animating = true;

    function tick(now) {
      const progress = clamp((now - startedAt) / duration, 0, 1);
      const eased = ease(progress);
      window.scrollTo(0, startY + (targetY - startY) * eased);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(tick);
        return;
      }

      window.scrollTo(0, targetY);
      animationFrame = 0;
      animating = false;
    }

    animationFrame = requestAnimationFrame(tick);
  }

  function go(direction) {
    rebuildCheckpoints();
    const fromY = window.scrollY;
    const index = nextCheckpointIndex(direction, fromY);
    if (index < 0) return;

    const target = checkpoints[index];
    const mode = insideLegacy(fromY) || insideLegacy(target.y) || target.chapterId === 'legacy'
      ? 'legacy'
      : 'smooth';
    animateTo(target.y, mode);
  }

  function resetGestureSoon() {
    window.clearTimeout(gestureResetTimer);
    gestureResetTimer = window.setTimeout(() => {
      wheelAccumulator = 0;
      wheelDirection = 0;
      gestureConsumed = false;
    }, gestureIdleMs);
  }

  window.addEventListener('wheel', (event) => {
    if (event.ctrlKey || event.metaKey) return;

    const target = event.target instanceof Element ? event.target : null;
    if (target?.closest('input, textarea, select')) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    const modeScale = event.deltaMode === 1 ? 24 : event.deltaMode === 2 ? window.innerHeight : 1;
    const delta = clamp(event.deltaY * modeScale, -160, 160);
    if (!delta) return;

    const direction = delta > 0 ? 1 : -1;
    if (wheelDirection && wheelDirection !== direction) wheelAccumulator = 0;
    wheelDirection = direction;

    resetGestureSoon();
    if (gestureConsumed || animating) return;

    wheelAccumulator += delta;
    if (Math.abs(wheelAccumulator) < wheelThreshold) return;

    gestureConsumed = true;
    wheelAccumulator = 0;
    go(direction);
  }, { passive: false, capture: true });

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest('button');
    if (!button) return;

    if (button === prevButton || button === nextButton || button === restartButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (animating) return;

      if (button === restartButton) {
        rebuildCheckpoints();
        const first = checkpoints[0];
        if (first) animateTo(first.y, 'smooth');
        return;
      }

      go(button === nextButton ? 1 : -1);
    }
  }, true);

  document.addEventListener('keydown', (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (target?.closest('input, textarea, select, button, a')) return;
    if (event.repeat || animating) return;

    if (['ArrowDown', 'ArrowRight', 'PageDown'].includes(event.key)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      go(1);
    } else if (['ArrowUp', 'ArrowLeft', 'PageUp'].includes(event.key)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      go(-1);
    }
  }, true);

  window.addEventListener('resize', () => {
    stopAnimation();
    rebuildCheckpoints();
  });

  window.addEventListener('mousedown', (event) => {
    if (event.button === 1) stopAnimation();
  }, { capture: true });

  rebuildCheckpoints();
  window.checkpointScroll = {
    next: () => go(1),
    previous: () => go(-1),
    rebuild: rebuildCheckpoints
  };
})();
