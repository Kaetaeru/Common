# Interactive Web Portfolio — Storyboard Plan

## Status

- Phase: planning only
- Existing `website-demo/` is considered deprecated for the new direction and will not be reused as a design foundation.
- New implementation should begin under `website-presentation/` only after the storyboard is locked.

## Product definition

This is not a conventional freelance landing page.

It is a browser-based interactive presentation / showreel that demonstrates what kinds of web experiences can be designed and built.

The core message is:

> 원하는 웹 경험을 디자인하고 실제로 작동하게 만들 수 있습니다.

The presentation should make the viewer think:

1. 단순 홈페이지뿐 아니라 다양한 인터랙션과 기능도 만들 수 있다.
2. 한 가지 스타일만 반복하는 것이 아니라 여러 시각 방향을 구현할 수 있다.
3. 원하는 결과를 설명하면 실제 작동하는 웹으로 만들 수 있다.
4. 한번 맡겨보고 싶다.

## Presentation grammar

- Full-screen presentation rather than a long landing page.
- One scene / slide = one main message.
- Navigation should support mouse wheel, keyboard arrows, and visible previous/next controls.
- A viewer should understand each scene in roughly 10–20 seconds.
- Slides should follow this basic pattern whenever possible:
  1. Claim
  2. Live demonstration
  3. Very short explanation
- Prefer showing capability directly instead of describing technical implementation.
- Avoid developer-facing boasts such as framework names unless they materially help the demonstration.

## Persistent presentation frame

The overall presentation frame should remain consistent even when each demo scene has a completely different visual style.

Possible persistent elements:

- Slide number, e.g. `03 / 08`
- Capability name, e.g. `INTERACTION`
- Previous / Next controls
- Progress indicator
- Optional small project identity / mark

The inner demo canvas may change radically from slide to slide.

This distinction is important:

- Frame = consistent presentation identity
- Demo canvas = intentionally varied design language

## Capability range — tentative, not locked

The first version should probably contain roughly 7–8 scenes.

Potential capabilities:

1. Opening / Introduction
2. Visual Design / Style Range
3. Responsive Design
4. Interaction
5. Motion
6. Functional UI / Mini App
7. Data / Dashboard
8. Closing / Contact

This list is a working hypothesis. Each slide must earn its place by proving a distinct capability.

## Anti-template / anti-AI-default rules

The presentation shell should not default to common generated SaaS landing-page patterns.

Do not use the following as default visual language:

- Bento grid
- Decorative gradient blobs without purpose
- Glassmorphism
- Fake developer terminal
- Pill components everywhere
- Uniform large border radius on every component
- Identical fade-up animation on every section
- Excessive English eyebrow labels
- Meaningless statistics
- Generic abstract marketing copy
- One visual theme applied to every demonstration

These patterns may still appear inside a specific slide if that slide intentionally demonstrates that particular style.

## Technical boundary for the first implementation

Keep the implementation small until the storyboard proves a need for more.

Expected initial structure:

```text
website-presentation/
  index.html
  style.css
  script.js
  STORYBOARD.md
```

Do not introduce a framework or component system unless a storyboard requirement actually needs it.

## Slide design template

Each slide should be decided using the same checklist.

### Slide XX — NAME

**Purpose**
- What capability does this scene prove?

**Viewer takeaway**
- What exact thought should the viewer have after seeing it?

**Opening state**
- What is visible the instant the scene appears?

**Live demonstration**
- What changes or happens on screen?

**Viewer interaction**
- What can the viewer click, drag, hover, type, scroll, or control?

**Visual language**
- What kind of design world does this scene use?
- How is it intentionally different from adjacent scenes?

**Copy**
- Main sentence
- Optional supporting sentence

**Transition in**
- How does the previous scene hand off into this one?

**Transition out**
- How does this scene lead naturally to the next capability?

**Proof condition**
- What must visibly work for this scene to successfully prove the claimed capability?

**Failure / delete condition**
- When should this slide be removed instead of polished further?

## Current work order

Do not design every slide at once.

Lock them sequentially:

1. Slide 01 — Opening
2. Slide 02 — next capability only after Slide 01 is stable
3. Continue one slide at a time

For every slide, first decide the experience and proof condition. Visual styling comes after that.

## Current focus

### Slide 01 — Opening

Not yet locked.

Questions to resolve:

- What should the viewer understand in the first 3 seconds?
- Should the opening immediately demonstrate something, or behave as a title card before the first demo?
- What single interaction, if any, best communicates that this is an interactive presentation rather than a normal portfolio page?
- How much identity / personal branding should appear before the work itself?
- What transition should hand the viewer into Slide 02?
