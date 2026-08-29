# Slide 02 — Visual Design / Same Content, Different Worlds

Status: concept direction locked; exact fictional brand content and final art direction references are not yet locked.

`STORYBOARD.md` remains the master presentation plan. This note defines the Slide 02 interaction and visual-range choreography before it is folded into the master storyboard.

## Purpose

Prove visual-design range without changing the underlying brief or content.

The viewer should see the exact same website content transformed into several clearly different contemporary design languages.

Viewer takeaway:

> 같은 내용도 목적과 분위기에 따라 전혀 다른 디자인으로 만들 수 있구나.

The point is not to show four templates. The point is to show one brief being interpreted four different ways.

## Portfolio-level message

Recommended outer caption:

> 내용은 그대로. 인상은 전혀 다르게.

Optional supporting line:

> 같은 정보도 타이포그래피, 레이아웃, 색, 이미지 처리와 움직임에 따라 완전히 다른 브랜드가 됩니다.

This explanatory copy belongs to the persistent exhibition frame, not inside the fictional demo website.

## Same-content invariant

All style states must preserve the same underlying content and information hierarchy.

The demo should reuse the same conceptual content nodes:

- brand / project name
- primary headline
- supporting description
- one primary CTA
- one secondary action or navigation item
- one hero visual / product object
- a small set of supporting facts or metadata

The words and meaning do not change between styles.

Invariant:

> Theme changes may alter presentation, but not the actual brief, message, or available information.

This is what makes the comparison credible.

## Recommended number of styles

Use four style states.

Four is enough to establish range while keeping the internal sequence short enough that Slide 02 does not consume the whole presentation.

Persistent deck metadata stays `02 / 08` throughout this sequence.

A smaller local indicator may show:

`STYLE 01 / 04`

through

`STYLE 04 / 04`.

## Proposed contemporary style sequence

The sequence should move through clearly distinct worlds. Do not use the Retro / Legacy language here because Slide 05 owns that contrast.

### Style 01 — Editorial / Luxury

Character:

- warm or neutral light surface
- serif-led typography
- large negative space
- asymmetric editorial composition
- restrained controls
- large visual treated like art direction rather than a product card

Message proved:

> 절제되고 고급스러운 브랜드 표현도 가능하다.

This should be the first actual portfolio work the viewer sees, so it needs to feel unusually polished rather than merely safe.

### Style 02 — Swiss / Functional

Character:

- strict grid
- strong typographic hierarchy
- highly legible sans-serif system
- limited color palette
- visible alignment logic
- functional navigation and information density

Message proved:

> 같은 내용을 훨씬 명확하고 구조적인 방향으로 만들 수도 있다.

The transition from Style 01 should visibly tighten and reorganize the composition rather than merely recolor it.

### Style 03 — Playful / Expressive

Character:

- confident color
- oversized type
- more elastic spacing
- expressive shape or image cropping
- responsive, tactile micro-motion
- playful controls without becoming childish

Message proved:

> 브랜드가 원한다면 훨씬 대담하고 개성 있는 웹도 가능하다.

This state should feel authored and lively, not like generic pastel SaaS UI.

### Style 04 — Cinematic / Immersive

Character:

- dark or image-dominant environment
- strong depth and scale
- minimal but deliberate text
- atmospheric motion tied to the hero visual
- content layered into a more immersive composition

Avoid neon gradients, glowing SaaS cards, or fake developer aesthetics.

Message proved:

> 같은 정보도 화면 전체를 경험처럼 사용하는 방향으로 만들 수 있다.

This is the final style state and should visually prepare the transition into Slide 03 rather than ending on a static card.

## Interaction ownership

Slide 02 temporarily owns wheel / arrow input as an internal style timeline.

Conceptual states:

`style-01 -> style-02 -> style-03 -> style-04 -> complete`

Rules:

- entering Slide 02 lands on Style 01.
- one deliberate downward navigation intent advances at most one style.
- one deliberate upward intent returns at most one style.
- while a style transformation is settling, duplicate input cannot skip a style.
- only after Style 04 has fully settled does the next deliberate downward intent advance to Slide 03.
- from Style 01, an upward intent may return to Slide 01.
- visible arrow controls and keyboard arrows follow the same internal state model as the wheel.

The local style indicator makes it clear that the viewer is progressing within Slide 02 rather than accidentally stuck.

## Transition choreography between styles

The website should transform, not be replaced by a screenshot carousel.

Preferred behavior:

1. Existing content begins responding to the navigation gesture.
2. Layout positions move toward the next composition.
3. Background / surface treatment changes.
4. Typography treatment changes as part of the morph.
5. Hero visual changes crop, scale, or framing while remaining recognizably the same visual subject.
6. Navigation and CTA restyle to match the new system.
7. The new theme settles into a fully usable state.

Where possible, the same visible elements should travel to their new positions so the viewer can track continuity.

Do not solve this as four unrelated full-screen images crossfading into each other.

## Scroll feel

Theme progression should feel continuous even though it resolves into four stable design states.

Small wheel movement may preview the next visual direction slightly, while a committed gesture completes the transformation.

The user should feel that the design is being re-authored under their input rather than that they clicked a theme switcher.

Do not require precise scrub control. The presentation still uses intentional gesture thresholds and stable resting states.

## Content choice requirements

The fictional content used for this demonstration must work convincingly in all four styles.

Prefer a simple brand / product brief with:

- one strong object or hero visual
- a short headline
- one short paragraph
- one CTA
- a few metadata items

Avoid content that inherently belongs to only one style, such as a gaming product that makes the luxury treatment feel absurd.

A furniture object, design object, small lifestyle product, exhibition, architecture studio, or similarly neutral subject would work well.

Exact fictional brand and copy remain to be chosen.

## Transition in from Slide 01

Slide 01 leaves the phrase:

> 직접 보여드리겠습니다.

briefly visible during the handoff.

The first Editorial / Luxury composition rises from below and takes visual control while that phrase yields to the outer Slide 02 caption:

> 내용은 그대로. 인상은 전혀 다르게.

The first real work should appear quickly; do not insert another title card between Slide 01 and the demo.

## Transition out to Slide 03

After Style 04 settles, the final visual state should provide a natural spatial setup for the Responsive demonstration.

Preferred handoff:

- the same demo website remains present,
- its outer composition begins to become more obviously browser-like / viewport-bound,
- the next committed downward gesture carries that same website into Slide 03,
- Slide 03 then demonstrates desktop -> phone -> tablet adaptation.

This creates continuity:

> 먼저 스타일을 바꿔 보여주고, 다음에는 같은 웹이 화면 크기에 맞춰 어떻게 바뀌는지 보여준다.

If feasible, Slide 02 and Slide 03 should reuse the same fictional content so the transition feels like one growing demonstration rather than unrelated samples.

## Proof condition

Slide 02 succeeds if a viewer can clearly tell that:

1. the content is the same,
2. the visual identity is materially different in every state,
3. the differences go beyond color swaps,
4. the transformation itself feels intentionally designed,
5. the viewer understands that this range can be applied to client work.

## Failure / delete conditions

Rework the slide if:

- the styles differ mostly by color,
- every style preserves the same card layout underneath,
- the viewer could reasonably mistake the sequence for four templates,
- the style changes take so many wheel gestures that the presentation feels stuck,
- one style looks intentionally weaker merely to make another look better,
- Style 04 duplicates the later Retro / Legacy joke,
- Slide 02 becomes longer or more impressive than the rest of the portfolio combined.
