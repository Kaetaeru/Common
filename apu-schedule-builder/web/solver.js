/* APU schedule solver.
 *
 * A direct port of the beam search in app_backend.py so the timetable can be
 * generated in the browser with no local server. app_backend.py stays the
 * reference implementation; tests/test_solver_parity.py checks that this file
 * and the Python original agree on real APU data.
 *
 * Loaded as a plain script in the browser and required by the parity test in Node.
 */

const APU_DAYS = ["MON", "TUE", "WED", "THU", "FRI"];
const APU_TIMETABLE_TERMS = new Set(["SEMESTER", "Q1", "Q2"]);

function apuSlotKey(quarter, day, period) {
  return `${quarter}:${day}:${period}`;
}

/** Quarter/day/period slots a Class occupies. SEMESTER classes occupy both quarters. */
function apuSectionSlots(section) {
  const term = Object.prototype.hasOwnProperty.call(section, "term") ? section.term : "SEMESTER";
  let quarters;
  if (term === "SEMESTER") quarters = ["Q1", "Q2"];
  else if (term === "Q1" || term === "Q2") quarters = [term];
  else quarters = [];

  const slots = new Set();
  for (const meeting of section.meetings || []) {
    const day = meeting.day;
    const period = meeting.period;
    if (!APU_DAYS.includes(day) || !Number.isInteger(period)) continue;
    for (const quarter of quarters) slots.add(apuSlotKey(quarter, day, period));
  }
  return slots;
}

function apuSetsOverlap(a, b) {
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  for (const value of small) if (large.has(value)) return true;
  return false;
}

function apuCodeText(value) {
  if (value === null || value === undefined) return "";
  let text = typeof value === "number" && Number.isInteger(value) ? String(value) : String(value).trim();
  if (/^\d+\.0$/.test(text)) text = text.slice(0, -2);
  return text;
}

/** Python's math.isclose(a, b, abs_tol=tol) with the default relative tolerance. */
function apuIsClose(a, b, absTol) {
  return Math.abs(a - b) <= Math.max(1e-9 * Math.max(Math.abs(a), Math.abs(b)), absTol);
}

/** Python's "%g" formatting for the credit figures shown in explanations. */
function apuFormatG(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(n);
  return Number.isInteger(n) ? String(n) : String(Number(n.toPrecision(6)));
}

function apuBlockedSlots(config) {
  const blocked = new Set();
  for (const value of config.blockedSlots || []) {
    if (typeof value !== "string") continue;
    const parts = value.split(":");
    if (parts.length !== 3) continue;
    const [quarter, day, periodText] = parts;
    if (!/^[+-]?\d+$/.test(periodText.trim())) continue;
    const period = parseInt(periodText, 10);
    if ((quarter === "Q1" || quarter === "Q2") && APU_DAYS.includes(day) && period >= 1 && period <= 6) {
      blocked.add(apuSlotKey(quarter, day, period));
    }
  }
  return blocked;
}

function apuMaxCreditsForSemester(level, accelerated) {
  if (accelerated && level >= 3) return 24;
  if (level <= 2) return 18;
  if (level <= 6) return 20;
  return 24;
}

function apuEmptyState() {
  return { chosen: [], occupied: new Set(), credits: 0, preferCount: 0, estimatedCreditCount: 0 };
}

function apuStateAdd(state, section, preferred) {
  const occupied = new Set(state.occupied);
  for (const slot of apuSectionSlots(section)) occupied.add(slot);
  return {
    chosen: state.chosen.concat([section]),
    occupied,
    credits: state.credits + Number(section.credits ?? 0),
    preferCount: state.preferCount + (preferred ? 1 : 0),
    estimatedCreditCount: state.estimatedCreditCount + (section.creditsEstimated ? 1 : 0),
  };
}

function apuScheduleMetrics(state) {
  const daysByQuarter = { Q1: new Set(), Q2: new Set() };
  const periodsByDay = new Map();
  for (const slot of state.occupied) {
    const [quarter, day, periodText] = slot.split(":");
    daysByQuarter[quarter].add(day);
    const key = `${quarter}:${day}`;
    if (!periodsByDay.has(key)) periodsByDay.set(key, []);
    periodsByDay.get(key).push(Number(periodText));
  }

  const campusDays = Math.max(daysByQuarter.Q1.size, daysByQuarter.Q2.size);
  let gaps = 0;
  let maxGap = 0;
  let earliest = 6;
  let latest = 1;
  for (const list of periodsByDay.values()) {
    const sorted = [...new Set(list)].sort((a, b) => a - b);
    if (!sorted.length) continue;
    earliest = Math.min(earliest, sorted[0]);
    latest = Math.max(latest, sorted[sorted.length - 1]);
    let dayMax = 0;
    for (let i = 1; i < sorted.length; i++) {
      const gap = Math.max(0, sorted[i] - sorted[i - 1] - 1);
      gaps += gap;
      if (gap > dayMax) dayMax = gap;
    }
    maxGap = Math.max(maxGap, dayMax);
  }

  const byIndex = (a, b) => APU_DAYS.indexOf(a) - APU_DAYS.indexOf(b);
  const anyOccupied = state.occupied.size > 0;
  return {
    campusDays,
    gaps,
    maxGap,
    earliest: anyOccupied ? earliest : null,
    latest: anyOccupied ? latest : null,
    daysByQuarter: {
      Q1: [...daysByQuarter.Q1].sort(byIndex),
      Q2: [...daysByQuarter.Q2].sort(byIndex),
    },
  };
}

const APU_SCORE_WEIGHTS = {
  fewest_days: { target: 14, prefer: 45, days: 30, gaps: 6, dayoff: 24, early: 8, late: 6, gapOver: 10, language: 3 },
  course_priority: { target: 12, prefer: 100, days: 8, gaps: 3, dayoff: 12, early: 5, late: 4, gapOver: 5, language: 4 },
  balanced: { target: 18, prefer: 70, days: 16, gaps: 6, dayoff: 22, early: 8, late: 6, gapOver: 8, language: 4 },
};

function apuStateScore(state, config, variant) {
  const target = Number(config.targetCredits ?? 18);
  const metrics = apuScheduleMetrics(state);
  const daysOff = new Set(config.daysOff || []);
  const earliestPref = parseInt(config.earliestPeriod ?? 1, 10);
  const latestPref = parseInt(config.latestPeriod ?? 6, 10);
  const maxDaysPref = parseInt(config.maxCampusDays ?? 5, 10);
  const maxGapPref = parseInt(config.maxGap ?? 5, 10);
  const preferredLanguages = new Set(
    (config.preferredLanguages || [])
      .filter((v) => String(v).trim())
      .map((v) => String(v).toUpperCase())
  );
  const weights = APU_SCORE_WEIGHTS[variant] || APU_SCORE_WEIGHTS.balanced;

  let score = 500.0;
  score -= Math.abs(target - state.credits) * weights.target;
  if (apuIsClose(target, state.credits, 0.01)) score += 90;
  score += state.preferCount * weights.prefer;
  score -= metrics.campusDays * weights.days;
  if (metrics.campusDays <= maxDaysPref) score += 30;
  score -= metrics.gaps * weights.gaps;

  const occupiedDays = new Set([...metrics.daysByQuarter.Q1, ...metrics.daysByQuarter.Q2]);
  let dayOffHits = 0;
  for (const day of daysOff) if (occupiedDays.has(day)) dayOffHits += 1;
  score -= dayOffHits * weights.dayoff;

  if (metrics.earliest !== null && metrics.earliest < earliestPref) {
    score -= (earliestPref - metrics.earliest) * weights.early;
  }
  if (metrics.latest !== null && metrics.latest > latestPref) {
    score -= (metrics.latest - latestPref) * weights.late;
  }
  if (metrics.maxGap > maxGapPref) score -= (metrics.maxGap - maxGapPref) * weights.gapOver;

  if (preferredLanguages.size) {
    let languageMatches = 0;
    for (const section of state.chosen) {
      const tokens = String(section.language ?? "").toUpperCase().split(/[^A-Z]+/).filter(Boolean);
      if (tokens.some((token) => preferredLanguages.has(token))) languageMatches += 1;
    }
    score += languageMatches * weights.language;
  }
  score -= state.estimatedCreditCount * 1.5;
  return score;
}

const APU_LANG_JA = "JA";
const APU_LANG_EN = "EN";

/** Port of language_rules.language_eligibility_reason. */
function apuLanguageEligibilityReason(subject, config) {
  const core = String(subject.languageCore ?? "").toUpperCase();
  const rank = parseInt(subject.languageLevelRank ?? 0, 10) || 0;
  if (!core || !rank) return "";

  const track = String(config.track || "E").toUpperCase();
  let completed = Math.max(0, parseInt(config.languageLevel ?? 0, 10) || 0);

  if (track === "E" && core === APU_LANG_EN) return "English Basis · core English level course";
  if ((track === "JST" || track === "JAT") && core === APU_LANG_JA) {
    return "Japanese Basis · core Japanese level course";
  }
  if (track === "JAT" && core === APU_LANG_EN) completed = Math.max(completed, 4);

  const opposite =
    (track === "E" && core === APU_LANG_JA) ||
    ((track === "JST" || track === "JAT") && core === APU_LANG_EN);
  if (opposite && completed && rank <= completed) {
    const label = String(subject.languageLevelLabel || subject.name || "language course");
    return `${label} · at or below completed language level`;
  }
  return "";
}

/** Port of language_rules.filter_candidate_subjects: solver candidates only. */
function apuFilterCandidateSubjects(data, config) {
  return Object.assign({}, data, {
    subjects: (data.subjects || []).filter((s) => !apuLanguageEligibilityReason(s, config)),
  });
}

function apuEligibleSections(subject, semesterLevel) {
  const minimum = subject.availableFromSemester;
  if (minimum && semesterLevel < parseInt(minimum, 10)) return [];
  return (subject.sections || []).filter((s) => APU_TIMETABLE_TERMS.has(s.term));
}

function apuValidateFixed(fixedSections, maxCredits) {
  let state = apuEmptyState();
  const seenSubjects = new Set();
  for (const section of fixedSections) {
    if (seenSubjects.has(section.subjectCode)) {
      return [null, `Fixed classes contain multiple sections of ${section.name}.`];
    }
    if (apuSetsOverlap(state.occupied, apuSectionSlots(section))) {
      return [null, `Fixed class ${section.name} conflicts with another fixed class.`];
    }
    state = apuStateAdd(state, section, false);
    seenSubjects.add(section.subjectCode);
  }
  if (state.credits > maxCredits) {
    return [null, `Fixed classes already exceed the ${apuFormatG(maxCredits)}-credit limit.`];
  }
  return [state, null];
}

function apuCompareText(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function apuSignature(state) {
  return state.chosen.map((s) => String(s.classCode)).sort().join("|");
}

function apuSolveVariant(data, config, variant, beamSize = 220) {
  // The language profile drops core level courses the student cannot register for.
  data = apuFilterCandidateSubjects(data, config);
  const semesterLevel = parseInt(config.semesterLevel ?? 5, 10);
  const accelerated = Boolean(config.accelerated);
  const hardMax = apuMaxCreditsForSemester(semesterLevel, accelerated);
  const requestedMax = Number(config.maxCredits ?? hardMax);
  const maxCredits = Math.min(hardMax, requestedMax);
  const target = Math.min(Number(config.targetCredits ?? 18), maxCredits);
  const statuses = new Map(
    Object.entries(config.statuses || {}).map(([k, v]) => [String(k), String(v).toUpperCase()])
  );
  const autofill = Boolean(config.autofill);
  const blockedSlots = apuBlockedSlots(config);

  const sectionByCode = new Map();
  for (const section of data.sections) sectionByCode.set(String(section.classCode), section);

  const fixedCodes = (config.fixedClassCodes || []).map(apuCodeText).filter(Boolean);
  const missingFixed = fixedCodes.filter((code) => !sectionByCode.has(code));
  if (missingFixed.length) {
    return [[], [`Fixed class code not found: ${missingFixed.join(", ")}`]];
  }

  const fixedSections = fixedCodes.map((code) => sectionByCode.get(code));
  for (const section of fixedSections) {
    const minimum = section.availableFromSemester;
    if (minimum && semesterLevel < parseInt(minimum, 10)) {
      return [[], [`Fixed class ${section.name} requires semester ${parseInt(minimum, 10)} or later.`]];
    }
    if (apuSetsOverlap(apuSectionSlots(section), blockedSlots)) {
      return [[], [`Fixed class ${section.name} is in a disabled time slot.`]];
    }
  }
  const [initial, fixedError] = apuValidateFixed(fixedSections, maxCredits);
  if (fixedError) return [[], [fixedError]];

  const fixedSubjects = new Set(fixedSections.map((s) => s.subjectCode));
  let subjects = [];
  const errors = [];

  for (const subject of data.subjects) {
    const code = subject.subjectCode;
    const status = statuses.get(code) || "NEUTRAL";
    if (status === "EXCLUDE" || fixedSubjects.has(code)) continue;
    const sections = apuEligibleSections(subject, semesterLevel);
    if (!sections.length) {
      if (status === "MUST") {
        errors.push(`${subject.name} is marked MUST but has no eligible AY2026 Fall section for semester ${semesterLevel}.`);
      }
      continue;
    }
    const availableSections = sections.filter((s) => !apuSetsOverlap(apuSectionSlots(s), blockedSlots));
    if (!availableSections.length) {
      if (status === "MUST") {
        errors.push(`${subject.name} is MUST, but all eligible sections use disabled time slots.`);
      }
      continue;
    }
    if (status === "MUST" || status === "PREFER" || autofill) {
      subjects.push([subject, status, availableSections]);
    }
  }

  if (errors.length) return [[], errors];

  // Required and preferred subjects are processed first; neutral autofill comes later.
  const rank = { MUST: 0, PREFER: 1, NEUTRAL: 2 };
  subjects.sort((a, b) => {
    const ra = rank[a[1]] ?? 2;
    const rb = rank[b[1]] ?? 2;
    return ra !== rb ? ra - rb : apuCompareText(a[0].name, b[0].name);
  });
  if (autofill) {
    // A bounded neutral pool keeps the local solver responsive without hiding selected courses.
    const selected = subjects.filter((x) => x[1] !== "NEUTRAL");
    const neutral = subjects.filter((x) => x[1] === "NEUTRAL");
    neutral.sort((a, b) => {
      const sa = a[0].availableFromSemester || 1;
      const sb = b[0].availableFromSemester || 1;
      return sa !== sb ? sa - sb : apuCompareText(a[0].name, b[0].name);
    });
    subjects = selected.concat(neutral.slice(0, 120));
  }

  const scoreConfig = Object.assign({}, config, { targetCredits: target });
  let beam = [initial];
  for (const [subject, status, sections] of subjects) {
    const nextBeam = [];
    const must = status === "MUST";
    const preferred = status === "PREFER";
    for (const state of beam) {
      if (!must) nextBeam.push(state);
      for (const section of sections) {
        const credits = Number(section.credits ?? subject.credits ?? 2);
        if (state.credits + credits > maxCredits + 1e-9) continue;
        if (apuSetsOverlap(state.occupied, apuSectionSlots(section))) continue;
        nextBeam.push(apuStateAdd(state, section, preferred));
      }
    }

    if (!nextBeam.length) {
      if (must) {
        return [[], [`${subject.name} is MUST, but every section conflicts with required/fixed classes or the credit limit.`]];
      }
      continue;
    }

    const scored = nextBeam.map((state) => [apuStateScore(state, scoreConfig, variant), state]);
    scored.sort((a, b) => b[0] - a[0]);
    // Deduplicate by selected class codes.
    const seen = new Set();
    beam = [];
    for (const [, state] of scored) {
      const signature = apuSignature(state);
      if (seen.has(signature)) continue;
      seen.add(signature);
      beam.push(state);
      if (beam.length >= beamSize) break;
    }
  }

  const ranked = beam
    .map((state) => [apuStateScore(state, scoreConfig, variant), state])
    .sort((a, b) => b[0] - a[0]);
  return [ranked.slice(0, 30), []];
}

function apuResultFromState(label, score, state, config) {
  const metrics = apuScheduleMetrics(state);
  const target = Number(config.targetCredits ?? 18);
  const daysOff = new Set(config.daysOff || []);
  const occupiedDays = new Set([...metrics.daysByQuarter.Q1, ...metrics.daysByQuarter.Q2]);
  const explanations = [];

  if (apuIsClose(state.credits, target, 0.01)) {
    explanations.push(`Target ${apuFormatG(target)} credits reached`);
  } else {
    explanations.push(`${apuFormatG(state.credits)} credits selected (target ${apuFormatG(target)})`);
  }
  if (state.preferCount) explanations.push(`${state.preferCount} preferred course(s) included`);
  const blockedCount = apuBlockedSlots(config).size;
  if (blockedCount) explanations.push(`${blockedCount} blocked time slot(s) respected`);

  const freeRequested = [...daysOff].filter((d) => !occupiedDays.has(d));
  if (freeRequested.length) {
    freeRequested.sort((a, b) => APU_DAYS.indexOf(a) - APU_DAYS.indexOf(b));
    explanations.push("Requested day(s) off kept: " + freeRequested.join(", "));
  }
  explanations.push(`Maximum ${metrics.campusDays} campus day(s) in a quarter`);
  if (metrics.gaps === 0) {
    explanations.push("No timetable gaps");
  } else if (metrics.maxGap <= parseInt(config.maxGap ?? 5, 10)) {
    explanations.push(`Longest gap is ${metrics.maxGap} period(s)`);
  }
  if (config.earliestPeriod !== undefined && metrics.earliest !== null && metrics.earliest >= parseInt(config.earliestPeriod, 10)) {
    explanations.push(`No class before period ${parseInt(config.earliestPeriod, 10)}`);
  }
  if (config.latestPeriod !== undefined && metrics.latest !== null && metrics.latest <= parseInt(config.latestPeriod, 10)) {
    explanations.push(`No class after period ${parseInt(config.latestPeriod, 10)}`);
  }

  const warnings = [];
  if (state.estimatedCreditCount) {
    warnings.push(`${state.estimatedCreditCount} course(s) use fallback 2-credit estimates because subject-list metadata did not match.`);
  }

  return {
    label,
    score: Math.round(score * 10) / 10,
    credits: state.credits,
    courses: state.chosen,
    metrics,
    explanations,
    warnings,
  };
}

const APU_VARIANTS = [
  ["BALANCED", "balanced"],
  ["FEWEST DAYS", "fewest_days"],
  ["COURSE PRIORITY", "course_priority"],
];

function apuGenerateSchedules(data, config) {
  const pools = [];
  const allErrors = [];
  for (const [label, variant] of APU_VARIANTS) {
    const [ranked, errors] = apuSolveVariant(data, config, variant);
    allErrors.push(...errors);
    for (const [score, state] of ranked) pools.push([label, score, state]);
  }

  if (!pools.length) {
    const unique = [...new Set(allErrors)];
    return { results: [], errors: unique.length ? unique : ["No valid schedule found."] };
  }

  const results = [];
  const seen = new Set();

  // First try each variant's best unique schedule.
  for (const [label] of APU_VARIANTS) {
    for (const [poolLabel, score, state] of pools) {
      if (poolLabel !== label) continue;
      const signature = apuSignature(state);
      if (seen.has(signature)) continue;
      seen.add(signature);
      results.push(apuResultFromState(label, score, state, config));
      break;
    }
  }

  // Fill up to three with the best remaining unique alternatives.
  if (results.length < 3) {
    const byScore = pools.slice().sort((a, b) => b[1] - a[1]);
    for (const [, score, state] of byScore) {
      const signature = apuSignature(state);
      if (seen.has(signature)) continue;
      seen.add(signature);
      results.push(apuResultFromState("ALTERNATIVE", score, state, config));
      if (results.length >= 3) break;
    }
  }

  return { results: results.slice(0, 3), errors: [] };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    apuGenerateSchedules,
    apuSolveVariant,
    apuScheduleMetrics,
    apuStateScore,
    apuSectionSlots,
    apuLanguageEligibilityReason,
    apuFilterCandidateSubjects,
  };
}
