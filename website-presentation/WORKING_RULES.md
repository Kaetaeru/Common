# Website Presentation — Working Rules

Status: ACTIVE

This file defines how design decisions are handled while the interactive portfolio storyboard is being developed.

## Latest reset directive — transition first

The current implementation is a clean rebuild. Previous implementation mechanics are not a foundation and should not be preserved for compatibility.

When an older planning note conflicts with the rules below, these rules take precedence for implementation:

1. Transition quality is the highest-priority interaction requirement.
2. Scrolling must produce visible continuous intermediate frames; the experience must not feel like `input -> state swap -> animation after the fact`.
3. A real continuous scroll / sticky scrollytelling architecture is allowed when it produces the intended presentation feel, even if an older note assumed discrete slide navigation.
4. Slide 02 theme changes and Slide 03 device changes should be driven by scroll progress wherever practical rather than by abrupt class swaps.
5. The Retro / Legacy scene remains the intentional exception where motion may become stepped or dated.
6. Anti-template / anti-AI-default guidance is secondary. Do not distort a good design merely to avoid patterns associated with generated websites.
7. Keep the existing storyboard goals, slide order, shared VELLUM / ARC 01 content, responsive choreography, and legacy contrast unless the user explicitly changes them.

## Decision boundary

Discuss and lock together only decisions that materially change the experience, structure, message, or proof of capability.

Examples that should be surfaced before implementation:

- what each slide is trying to prove,
- slide order,
- interaction model,
- scroll / wheel ownership,
- major transition concepts,
- whether a slide introduces a new capability,
- whether the same content continues across slides,
- changes that could confuse the viewer or contradict the presentation grammar.

## Designer discretion

Detailed art-direction and implementation choices may be decided during build and reviewed afterward in the working result.

Examples:

- exact font size and line height,
- spacing and alignment,
- precise color values,
- image crop and scale,
- local composition,
- button shape and control styling,
- micro-animation timing,
- easing curves,
- small decorative details,
- responsive spacing adjustments,
- exact visual treatment inside an already-approved theme.

These details should obey accessibility requirements and the overall Interactive Design Exhibition concept. Anti-template guidance may inform choices but is not a hard visual prohibition.

## Review model

The implementation should first make a coherent design judgment rather than asking for approval on every small choice.

The user reviews the actual result afterward and requests revisions where needed.

If a small-looking decision would materially alter the established experience or make a later slide impossible, it stops being a detail and must be surfaced as a structural decision.

## Current implication

For Slide 02 and later slides:

- preserve the approved concept and interaction choreography,
- make transition behavior observable during the user's scroll itself,
- choose detailed composition autonomously,
- build a coherent working version,
- then review visually and iterate.
