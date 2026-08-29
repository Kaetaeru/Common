# Interactive Web Portfolio — Storyboard Plan

## Status

- Phase: storyboard planning only
- Existing `website-demo/` is deprecated for the new direction and will not be reused as a design foundation.
- New implementation begins under `website-presentation/` only after the storyboard is sufficiently locked.
- Slide 01 — Opening: LOCKED at concept level.
- Presentation shell theme: LOCKED at concept level.

## Product definition

This is not a conventional freelance landing page.

It is a browser-based interactive presentation / showreel that demonstrates what kinds of web experiences can be designed and built.

The core message is:

> 원하는 웹 경험을 디자인하고 실제로 작동하게 만들 수 있습니다.

The presentation should make the viewer think:

1. 단순 홈페이지뿐 아니라 다양한 인터랙션과 기능도 만들 수 있다.
2. 한 가지 스타일만 반복하는 것이 아니라 여러 시각 방향을 구현할 수 있다.
3. 세련된 최신 스타일뿐 아니라 의도적인 레트로 / 구식 웹 스타일도 구현할 수 있다.
4. 원하는 결과를 설명하면 실제 작동하는 웹으로 만들 수 있다.
5. 한번 맡겨보고 싶다.

## Presentation concept — Interactive Design Exhibition

The presentation shell should feel like a restrained design exhibition / interactive showroom rather than a SaaS landing page.

The viewer is not reading one long website. They are moving through a sequence of exhibits.

### Shell character

- Neutral, quiet, typography-led presentation frame.
- Visual reference: exhibition caption system, design catalogue, gallery wayfinding, editorial portfolio.
- Prefer near-black, off-white, or paper-like neutral surfaces for the shell.
- At most one restrained identity accent color for the shell.
- Thin rules, precise spacing, compact metadata, strong typography.
- Avoid decorative components that compete with the demo canvas.
- The shell should look designed, but should never imply that every client site would share this aesthetic.

### Important separation

- Presentation frame = consistent exhibition identity.
- Demo canvas = a different commissioned world on every capability slide.

The frame demonstrates taste and control.
The canvas demonstrates range.

### Why this theme

A highly branded shell would make viewers assume that one visual style is the creator's only style. A neutral exhibition system lets radically different work coexist while still feeling like one deliberate presentation.

## Presentation grammar

- Full-screen presentation rather than a long landing page.
- One scene / slide = one main message.
- Navigation supports mouse wheel, keyboard arrows, and visible previous/next controls.
- A viewer should understand each scene in roughly 10–20 seconds.
- Slides should follow this pattern whenever possible:
  1. Claim
  2. Live demonstration
  3. Very short explanation
- Prefer showing capability directly instead of describing technical implementation.
- Avoid developer-facing boasts such as framework names unless they materially help the demonstration.
- Every slide must visibly prove something different.

## Persistent presentation frame

The overall presentation frame remains consistent even when each demo scene uses a radically different design language.

Expected persistent elements:

- Project identity / mark: `KAETARU / WEB`
- Slide number, e.g. `03 / 08`
- Capability label
- Previous / Next controls
- Progress indicator

These should behave more like gallery wayfinding than website navigation.

## Working capability sequence — 8 slides

The current sequence is intentionally compact. Interaction and motion are combined so the retro interlude can earn a full scene without bloating the presentation.

1. Opening / Introduction
2. Visual Design / Contemporary Style Range
3. Responsive Design
4. Interaction + Motion
5. Retro / Legacy Web — intentional contrast interlude
6. Functional UI / Mini App
7. Data / Dashboard
8. Closing / Contact

This order is not fully locked beyond Slide 01, but the retro capability should remain around the middle rather than at the beginning or end.

## Retro / Legacy Web principle

A deliberately old-fashioned website should appear mid-presentation as a contrast beat.

Its message is not:

> 옛날 사이트도 흉내낼 수 있습니다.

Its message is:

> 스타일은 목표에 맞춰 선택할 수 있습니다. 최신 유행만 반복하지 않습니다.

The scene may intentionally use visual conventions such as:

- browser-default blue links
- Times / system fonts
- table-like layout
- tiled background or flat page background
- bevelled or native-looking controls
- marquee-like motion only if intentionally controlled
- dense navigation / old portal structure
- low-resolution decorative treatment

However it must still be technically deliberate:

- readable
- responsive enough not to break the presentation
- keyboard accessible where relevant
- no accidental broken layout presented as retro styling

The contrast should feel authored, not sloppy.

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

These patterns may appear inside a specific demo canvas if that slide intentionally demonstrates that style.

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

Each slide is decided using the same checklist.

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

## Slide 01 — Opening — LOCKED

**Purpose**

Open the presentation, establish the presentation grammar, and teach navigation without behaving like a conventional portfolio homepage.

**Viewer takeaway**

> 설명을 읽는 포트폴리오가 아니라 직접 보면서 넘기는 인터랙티브 프레젠테이션이구나.

**First 3 seconds**

The viewer should understand only two things:

1. This presentation intends to show rather than explain.
2. There is a clear action that moves to the next scene.

**Opening state**

A highly restrained full-screen stage using the neutral exhibition shell.

Primary copy centered or compositionally dominant:

> 설명보다, 직접 보여드리겠습니다.

Supporting copy:

> 웹사이트 디자인 · 인터랙션 · 기능 구현

Persistent frame visible from the beginning:

- `KAETARU / WEB`
- `01 / 08`
- progress indicator
- previous / next controls

**Viewer interaction**

Only the presentation navigation is introduced here:

- mouse wheel
- keyboard arrow keys
- visible `NEXT` control

Do not add a second interactive gimmick on the opening slide.

**Visual language**

Neutral exhibition / editorial presentation shell. The opening itself should not look like one of the portfolio's demo styles.

Avoid on this slide:

- technology stack lists
- long biography
- service cards
- profile photography as the focal point
- decorative gradients
- multiple CTAs
- automatic decorative motion

**Transition out**

The copy itself participates in the transition.

`설명보다,` disappears first.

`직접 보여드리겠습니다.` remains briefly and becomes the semantic handoff into Slide 02, where the first real demonstration appears.

The transition should make the sentence true rather than merely animate the screen.

**Proof condition**

Without instructions or hesitation, the viewer can advance once and understands that the experience is slide-based and interactive.

**Failure / delete condition**

The opening fails if:

- it becomes more visually memorable than the actual demonstrations,
- the viewer mistakes it for a normal landing-page hero,
- the user has to search for how to continue,
- it introduces more than one interaction model at once.

## Current work order

Lock slides sequentially.

1. Slide 01 — Opening — LOCKED
2. Slide 02 — Visual Design / Contemporary Style Range — NEXT
3. Slide 03 only after Slide 02 is stable
4. Continue one slide at a time

For every slide, first decide the experience and proof condition. Visual styling comes after that.
