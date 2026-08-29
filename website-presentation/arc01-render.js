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

  let arcImageObjectUrl = null;

  async function restoreArcImageForPreview() {
    try {
      const source = 'https://raw.githubusercontent.com/Kaetaeru/Common/main/website-presentation/arc01-image.css';
      const response = await fetch(source, { cache: 'no-store' });
      if (!response.ok) throw new Error(`ARC image source returned ${response.status}`);
      const css = await response.text();
      const match = css.match(/data:image\/webp;base64,([A-Za-z0-9+/=]+)/);
      if (!match) throw new Error('ARC image data was not found');

      const binary = atob(match[1]);
      const bytes = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);

      arcImageObjectUrl = URL.createObjectURL(new Blob([bytes], { type: 'image/webp' }));
      document.documentElement.style.setProperty('--arc-image', `url("${arcImageObjectUrl}")`);
      document.documentElement.dataset.arcImageReady = 'true';
    } catch (error) {
      console.warn('ARC 01 image fallback could not be restored.', error);
    }
  }

  restoreArcImageForPreview();
  window.addEventListener('pagehide', () => {
    if (arcImageObjectUrl) URL.revokeObjectURL(arcImageObjectUrl);
  }, { once: true });

  const themes = [
    {
      name: 'EDITORIAL / LUXURY', surface: [239, 234, 224], fg: [22, 20, 18], accent: [165, 120, 70],
      photoX: 46, photoY: 0, photoW: 54, photoH: 100, photoPosX: 58, photoPosY: 50, photoScale: 1, photoRadius: 0,
      contain: 0, backdrop: 0, shade: 0,
      copyX: 5, copyY: 22, copyW: 36, title: 48, tag: 66,
      buyX: 5, buyY: 75, factsX: 5, factsY: 87, factsW: 36, grid: 0
    },
    {
      name: 'SWISS / FUNCTIONAL', surface: [248, 247, 243], fg: [16, 16, 15], accent: [228, 65, 49],
      photoX: 58, photoY: 10, photoW: 38, photoH: 78, photoPosX: 62, photoPosY: 50, photoScale: 1.03, photoRadius: 0,
      contain: 0, backdrop: 0, shade: 0,
      copyX: 4, copyY: 20, copyW: 46, title: 84, tag: 44,
      buyX: 4, buyY: 73, factsX: 4, factsY: 84, factsW: 50, grid: .62
    },
    {
      name: 'PLAYFUL / EXPRESSIVE', surface: [19, 57, 205], fg: [255, 244, 219], accent: [255, 201, 97],
      photoX: 47, photoY: 5, photoW: 48, photoH: 90, photoPosX: 60, photoPosY: 50, photoScale: 1.08, photoRadius: 0,
      contain: 0, backdrop: 0, shade: 0,
      copyX: 4, copyY: 18, copyW: 58, title: 104, tag: 72,
      buyX: 72, buyY: 77, factsX: 4, factsY: 83, factsW: 39, grid: 0
    },
    {
      name: 'CINEMATIC / IMMERSIVE', surface: [15, 13, 12], fg: [246, 237, 223], accent: [255, 192, 105],
      photoX: 0, photoY: 0, photoW: 100, photoH: 100, photoPosX: 70, photoPosY: 50, photoScale: 1, photoRadius: 0,
      contain: 1, backdrop: .9, shade: .86,
      copyX: 5, copyY: 55, copyW: 38, title: 42, tag: 58,
      buyX: 74, buyY: 79, factsX: 5, factsY: 88, factsW: 62, grid: 0
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
    const local = position - base;
    const t = smoothstep(local);
    const a = themes[base];
    const b = themes[next];

    const setVar = (name, value) => productDemo.style.setProperty(name, value);
    setVar('--surface', mixRgb(a.surface, b.surface, t));
    setVar('--fg', mixRgb(a.fg, b.fg, t));
    setVar('--accent', mixRgb(a.accent, b.accent, t));
    setVar('--photo-x', mix(a.photoX, b.photoX, t));
    setVar('--photo-y', mix(a.photoY, b.photoY, t));
    setVar('--photo-w', mix(a.photoW, b.photoW, t));
    setVar('--photo-h', mix(a.photoH, b.photoH, t));
    setVar('--photo-pos-x', mix(a.photoPosX, b.photoPosX, t));
    setVar('--photo-pos-y', mix(a.photoPosY, b.photoPosY, t));
    setVar('--photo-scale', mix(a.photoScale, b.photoScale, t));
    setVar('--photo-radius', mix(a.photoRadius, b.photoRadius, t));
    setVar('--contain-opacity', mix(a.contain, b.contain, t));
    setVar('--backdrop-opacity', mix(a.backdrop, b.backdrop, t));
    setVar('--shade-opacity', mix(a.shade, b.shade, t));
    setVar('--copy-x', mix(a.copyX, b.copyX, t));
    setVar('--copy-y', mix(a.copyY, b.copyY, t));
    setVar('--copy-w', mix(a.copyW, b.copyW, t));
    setVar('--title-size', mix(a.title, b.title, t));
    setVar('--tag-size', mix(a.tag, b.tag, t));
    setVar('--buy-x', mix(a.buyX, b.buyX, t));
    setVar('--buy-y', mix(a.buyY, b.buyY, t));
    setVar('--facts-x', mix(a.factsX, b.factsX, t));
    setVar('--facts-y', mix(a.factsY, b.factsY, t));
    setVar('--facts-w', mix(a.factsW, b.factsW, t));
    setVar('--grid-opacity', mix(a.grid, b.grid, t));

    const clarity = .52 + .48 * Math.abs(local * 2 - 1);
    setVar('--type-clarity', clarity);

    const nearest = Math.min(3, Math.round(position));
    productDemo.dataset.theme = String(nearest);
    styleName.textContent = themes[nearest].name;
    styleCount.textContent = `STYLE ${String(nearest + 1).padStart(2, '0')} / 04`;

    const handoff = smoothstep(range(p, .94, 1));
    productDemo.style.transform = `scale(${1 - handoff * .018}) translateY(${-handoff * 7}px)`;
    productDemo.style.boxShadow = `0 ${handoff * 26}px ${handoff * 70}px rgba(0,0,0,${handoff * .2})`;
  }

  function deviceGeometry(type) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (type === 'phone') {
      return { w: Math.min(380, vw * .82), h: Math.min(710, vh * .8), r: 40, border: 8, cameraW: 76, cameraH: 18, shadow: 330 };
    }
    if (type === 'tablet') {
      return { w: Math.min(860, vw * .86), h: Math.min(620, vh * .74), r: 28, border: 8, cameraW: 10, cameraH: 10, shadow: 610 };
    }
    return { w: Math.min(1080, vw * .72), h: Math.min(690, vh * .78), r: 10, border: 1, cameraW: 0, cameraH: 0, shadow: Math.min(700, vw * .55) };
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
    } else if (p < .42) {
      applyDeviceGeometry(phone, phone, 1);
      relativeScroll = smoothstep(range(p, .22, .42)) * .96;
      label = 'PHONE / LIVE SCROLL';
    } else if (p < .68) {
      const t = range(p, .42, .68);
      applyDeviceGeometry(phone, tablet, t);
      relativeScroll = mix(.96, .1, smoothstep(t));
      label = 'PHONE → TABLET';
    } else if (p < .9) {
      applyDeviceGeometry(tablet, tablet, 1);
      relativeScroll = mix(.1, .96, smoothstep(range(p, .68, .9)));
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
    deviceShell.style.transform = `translate3d(0, ${mix(24, 0, depth)}px, 0)`;
    deviceShadow.style.opacity = String(.5 + depth * .38);
  }

  function renderLegacy(scrollY) {
    const p = chapterProgress(legacyChapter, scrollY);
    const enter = range(p, 0, .22);
    const stepped = Math.round(enter * 5) / 5;
    legacyWindow.style.transform = `translateY(${(1 - stepped) * 28}px)`;
    legacyWindow.style.filter = enter < .12 ? 'brightness(1.18) contrast(.92)' : 'none';
  }

  let queued = false;
  function render() {
    queued = false;
    const y = window.scrollY;
    renderFrame(y);
    renderIntro(y);
    renderVisual(y);
    renderResponsive(y);
    renderLegacy(y);
  }

  function queueRender() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(render);
  }

  window.addEventListener('scroll', queueRender, { passive: true });
  window.addEventListener('resize', queueRender);
  requestAnimationFrame(render);
})();