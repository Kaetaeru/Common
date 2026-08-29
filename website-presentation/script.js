(() => {
  const slideCount = 8;
  const track = document.getElementById('slidesTrack');
  const presentation = document.getElementById('presentation');
  const slideNumber = document.getElementById('slideNumber');
  const slideLabel = document.getElementById('slideLabel');
  const progressFill = document.getElementById('progressFill');
  const prevButton = document.getElementById('prevButton');
  const nextButton = document.getElementById('nextButton');
  const openingHint = document.getElementById('openingHint');
  const legacyFlash = document.getElementById('legacyFlash');
  const productDemo = document.getElementById('productDemo');
  const styleName = document.getElementById('styleName');
  const styleCount = document.getElementById('styleCount');
  const deviceShell = document.getElementById('deviceShell');
  const deviceContent = document.getElementById('deviceContent');
  const devicePhaseLabel = document.getElementById('devicePhaseLabel');
  const lightToggle = document.getElementById('lightToggle');
  const roomDemo = document.getElementById('roomDemo');
  const restartButton = document.getElementById('restartButton');
  const dimmer = document.getElementById('dimmer');
  const dimmerOutput = document.getElementById('dimmerOutput');
  const configPreview = document.getElementById('configPreview');
  const finishButtons = [...document.querySelectorAll('.finish')];
  const productLightButton = productDemo.querySelector('.product-secondary');

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const themeClasses = ['theme-luxury', 'theme-swiss', 'theme-playful', 'theme-cinematic'];
  const themeNames = ['EDITORIAL / LUXURY', 'SWISS / FUNCTIONAL', 'PLAYFUL / EXPRESSIVE', 'CINEMATIC / IMMERSIVE'];
  const devicePhases = ['DESKTOP', 'PHONE', 'PHONE SCROLL', 'TABLET', 'TABLET SCROLL'];
  const smoothTrackTransition = 'transform 1050ms cubic-bezier(.12,.78,.18,1)';
  const legacyTrackTransition = 'transform 420ms steps(5, end)';
  const wheelCommitThreshold = 72;
  const wheelPreviewRatio = 0.24;

  let slideIndex = 0;
  let styleIndex = 0;
  let devicePhase = 0;
  let transitionLocked = false;
  let wheelAccumulator = 0;
  let wheelPreviewOffset = 0;
  let wheelSuppressed = false;
  let wheelIdleTimer = null;
  let lightOn = false;

  function updateFrame() {
    const slide = document.getElementById(`slide-${slideIndex + 1}`);
    slideNumber.textContent = `${String(slideIndex + 1).padStart(2, '0')} / 08`;
    slideLabel.textContent = slide.dataset.label;
    progressFill.style.width = `${((slideIndex + 1) / slideCount) * 100}%`;
    prevButton.disabled = slideIndex === 0 && styleIndex === 0;
    nextButton.disabled = slideIndex === slideCount - 1;
    document.body.classList.toggle('legacy-mode', slideIndex === 4);
  }

  function trackBasePosition(index = slideIndex) {
    return index * -presentation.clientHeight;
  }

  function setTrackPosition(index, legacy = false, immediate = false) {
    wheelPreviewOffset = 0;
    track.style.transition = immediate || prefersReducedMotion
      ? 'none'
      : legacy
        ? legacyTrackTransition
        : smoothTrackTransition;
    track.style.transform = `translate3d(0, ${trackBasePosition(index)}px, 0)`;
  }

  function canPreviewTrack(direction) {
    if (prefersReducedMotion || transitionLocked || slideIndex === 1 || slideIndex === 2) return false;
    const nextIndex = slideIndex + direction;
    if (nextIndex < 0 || nextIndex >= slideCount) return false;
    return slideIndex !== 4 && nextIndex !== 4;
  }

  function previewTrack(accumulatedDelta) {
    const direction = accumulatedDelta > 0 ? 1 : -1;
    if (!canPreviewTrack(direction)) return;

    const progress = Math.min(Math.abs(accumulatedDelta) / wheelCommitThreshold, 1);
    const easedProgress = 1 - ((1 - progress) * (1 - progress));
    wheelPreviewOffset = -direction * presentation.clientHeight * wheelPreviewRatio * easedProgress;
    track.style.transition = 'none';
    track.style.transform = `translate3d(0, ${trackBasePosition() + wheelPreviewOffset}px, 0)`;
  }

  function settleTrackPreview() {
    if (!wheelPreviewOffset) return;
    setTrackPosition(slideIndex, false, false);
  }

  function lockFor(ms = 1080) {
    transitionLocked = true;
    window.setTimeout(() => {
      transitionLocked = false;
      track.classList.remove('legacy-step');
    }, prefersReducedMotion ? 20 : ms);
  }

  function flashLegacy() {
    legacyFlash.classList.remove('active');
    void legacyFlash.offsetWidth;
    legacyFlash.classList.add('active');
  }

  function goToSlide(nextIndex) {
    if (nextIndex < 0 || nextIndex >= slideCount || nextIndex === slideIndex) return;
    const involvesLegacy = nextIndex === 4 || slideIndex === 4;
    if (involvesLegacy) flashLegacy();

    if (wheelPreviewOffset && !involvesLegacy && !prefersReducedMotion) {
      void track.offsetHeight;
    }

    slideIndex = nextIndex;
    if (slideIndex !== 1) styleIndex = slideIndex < 1 ? 0 : styleIndex;
    if (slideIndex !== 2 && nextIndex !== 2) deviceContent.scrollTop = 0;
    setTrackPosition(slideIndex, involvesLegacy);
    updateFrame();
    openingHint.classList.add('used');
    lockFor(involvesLegacy ? 520 : 1080);
  }

  function setStyle(index) {
    if (index < 0 || index >= themeClasses.length || index === styleIndex) return;
    styleIndex = index;
    productDemo.classList.remove(...themeClasses);
    productDemo.classList.add(themeClasses[styleIndex]);
    styleName.textContent = themeNames[styleIndex];
    styleCount.textContent = `STYLE ${String(styleIndex + 1).padStart(2, '0')} / 04`;
    lockFor(820);
  }

  function setDevicePhase(nextPhase) {
    if (nextPhase < 0 || nextPhase >= devicePhases.length || nextPhase === devicePhase) return;
    devicePhase = nextPhase;
    devicePhaseLabel.textContent = devicePhases[devicePhase];
    deviceShell.classList.remove('device-desktop', 'device-phone', 'device-tablet');

    if (devicePhase === 0) {
      deviceShell.classList.add('device-desktop');
      deviceContent.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    } else if (devicePhase <= 2) {
      deviceShell.classList.add('device-phone');
      deviceContent.scrollTo({ top: devicePhase === 2 ? deviceContent.scrollHeight * 0.46 : 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    } else {
      deviceShell.classList.add('device-tablet');
      deviceContent.scrollTo({ top: devicePhase === 4 ? deviceContent.scrollHeight * 0.4 : 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    }
    lockFor(980);
  }

  function navigate(direction) {
    if (transitionLocked) return;

    if (slideIndex === 1) {
      if (direction > 0 && styleIndex < 3) return setStyle(styleIndex + 1);
      if (direction < 0 && styleIndex > 0) return setStyle(styleIndex - 1);
      if (direction > 0) return goToSlide(2);
      return goToSlide(0);
    }

    if (slideIndex === 2) {
      if (direction > 0 && devicePhase < 4) return setDevicePhase(devicePhase + 1);
      if (direction < 0 && devicePhase > 0) return setDevicePhase(devicePhase - 1);
      if (direction > 0) return goToSlide(3);
      return goToSlide(1);
    }

    goToSlide(slideIndex + direction);
  }

  function releaseWheelWhenIdle() {
    window.clearTimeout(wheelIdleTimer);
    wheelIdleTimer = window.setTimeout(() => {
      wheelSuppressed = false;
      wheelAccumulator = 0;
      if (!transitionLocked) settleTrackPreview();
    }, 180);
  }

  presentation.addEventListener('wheel', (event) => {
    event.preventDefault();
    if (wheelSuppressed || transitionLocked) {
      releaseWheelWhenIdle();
      return;
    }

    if (Math.sign(event.deltaY) !== Math.sign(wheelAccumulator) && wheelAccumulator !== 0) {
      wheelAccumulator = 0;
      settleTrackPreview();
    }

    wheelAccumulator += event.deltaY;
    previewTrack(wheelAccumulator);

    if (Math.abs(wheelAccumulator) >= wheelCommitThreshold) {
      const direction = wheelAccumulator > 0 ? 1 : -1;
      wheelAccumulator = 0;
      wheelSuppressed = true;
      navigate(direction);
      releaseWheelWhenIdle();
      return;
    }

    releaseWheelWhenIdle();
  }, { passive: false });

  document.addEventListener('keydown', (event) => {
    const editable = event.target.matches('input, textarea, select');
    if (editable) return;
    if (['ArrowDown', 'ArrowRight'].includes(event.key)) {
      event.preventDefault();
      navigate(1);
    }
    if (['ArrowUp', 'ArrowLeft'].includes(event.key)) {
      event.preventDefault();
      navigate(-1);
    }
  });

  prevButton.addEventListener('click', () => navigate(-1));
  nextButton.addEventListener('click', () => navigate(1));
  restartButton.addEventListener('click', () => {
    styleIndex = 0;
    productDemo.classList.remove(...themeClasses);
    productDemo.classList.add(themeClasses[0]);
    styleName.textContent = themeNames[0];
    styleCount.textContent = 'STYLE 01 / 04';
    if (devicePhase !== 0) setDevicePhase(0);
    devicePhase = 0;
    devicePhaseLabel.textContent = devicePhases[0];
    deviceShell.classList.remove('device-phone', 'device-tablet');
    deviceShell.classList.add('device-desktop');
    deviceContent.scrollTop = 0;
    slideIndex = 0;
    setTrackPosition(0, false, true);
    openingHint.classList.remove('used');
    updateFrame();
  });

  function setRoomLight(on) {
    lightOn = on;
    roomDemo.classList.toggle('on', lightOn);
    lightToggle.setAttribute('aria-pressed', String(lightOn));
    lightToggle.textContent = lightOn ? '빛 끄기' : '빛 켜보기';
  }

  lightToggle.addEventListener('click', () => setRoomLight(!lightOn));
  productLightButton.addEventListener('click', () => {
    productDemo.classList.toggle('lamp-on');
    const isOn = productDemo.classList.contains('lamp-on');
    productDemo.querySelector('.lamp-glow').style.opacity = isOn ? '.62' : '';
    productLightButton.textContent = isOn ? '빛 끄기' : '빛 켜보기';
  });

  roomDemo.addEventListener('pointermove', (event) => {
    if (prefersReducedMotion) return;
    const rect = roomDemo.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    roomDemo.querySelector('.room-glow').style.transform = `translate(${x * 28}px, ${y * 18}px)`;
  });
  roomDemo.addEventListener('pointerleave', () => {
    roomDemo.querySelector('.room-glow').style.transform = '';
  });

  dimmer.addEventListener('input', () => {
    const value = Number(dimmer.value);
    dimmerOutput.value = `${value}%`;
    dimmerOutput.textContent = `${value}%`;
    configPreview.querySelector('.config-light').style.opacity = String(0.15 + value / 125);
    configPreview.querySelector('.config-beam').style.opacity = String(0.2 + value / 125);
  });

  finishButtons.forEach((button) => {
    button.addEventListener('click', () => {
      finishButtons.forEach((item) => {
        const active = item === button;
        item.classList.toggle('active', active);
        item.setAttribute('aria-pressed', String(active));
      });
      configPreview.classList.toggle('graphite', button.dataset.finish === 'graphite');
    });
  });

  window.addEventListener('resize', () => setTrackPosition(slideIndex, false, true));

  setTrackPosition(0, false, true);
  updateFrame();
})();
