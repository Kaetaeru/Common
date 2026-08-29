# Responsive Device Choreography

Status: concept locked, detailed Slide 03 composition not yet locked.

This note records the responsive-device transition behavior before Slide 03 is fully storyboarded. `STORYBOARD.md` remains the master presentation plan; this sequence should be folded into Slide 03 when that slide is formally locked.

## Goal

Do not merely show separate desktop, phone, and tablet screenshots.

The same live website should visibly transform from one responsive context into another so the viewer understands that the layout itself adapts and remains functional.

Viewer takeaway:

> 같은 웹을 데스크톱, 휴대폰, 태블릿에 맞게 실제로 재구성하고 동작하게 만들 수 있구나.

## Core sequence

### Stage A — Desktop / open canvas

The responsive demo begins as a full desktop-style website filling the demonstration canvas.

It behaves like a real website, not a screenshot.

### Stage B — Desktop becomes phone

As the viewer scrolls downward:

1. The current website begins to contract toward a portrait composition.
2. A phone frame gradually resolves around the content rather than appearing as a hard cut.
3. The content must not simply scale down like an image.
4. Responsive layout rules visibly reflow the content into a mobile arrangement: navigation, columns, typography, spacing, imagery, and controls adapt to the narrower width.
5. The transition settles with the same website fully alive inside the phone viewport.

The intended impression is that the website has been physically gathered into the device.

## Stage C — Live phone state

Once the phone is fully formed, the phone remains spatially stable while the next downward wheel input scrolls the website inside the phone screen.

Requirements:

- The outer presentation stage does not move during this phase.
- The phone hardware/frame remains stationary.
- Only the website inside the phone viewport scrolls.
- Buttons, menus, and other relevant controls remain real and interactive.
- The scroll demonstrates mobile content hierarchy rather than acting as decorative motion.

## Stage D — Phone becomes tablet

After the mobile demonstration reaches its intended endpoint, additional downward scroll begins the next responsive transformation.

1. Internal phone scrolling stops at the designed handoff point.
2. The phone composition expands and changes aspect ratio.
3. The phone frame transitions into a tablet frame rather than disappearing and being replaced by an unrelated mockup.
4. The same live website reflows again for tablet width.
5. Mobile-only layout decisions relax where appropriate: columns may return, navigation may widen, spacing changes, and content density increases.
6. The transformation settles with the website alive inside the tablet viewport.

The content must remain recognizably continuous throughout the transformation.

## Stage E — Live tablet state

Further downward scroll now moves the website inside the tablet viewport while the tablet itself remains spatially anchored.

This should demonstrate that tablet layout is a real intermediate responsive state, not simply a scaled desktop or oversized phone.

## Stage F — Exit to next presentation slide

Only after the tablet demonstration reaches its designed endpoint does a new deliberate downward navigation intent become eligible to advance to the next presentation slide.

The normal smooth vertical presentation transition then resumes.

## Input ownership / state model

This sequence is a deliberate exception to the normal rule that wheel input immediately means previous/next slide.

Inside the responsive demonstration, wheel input is owned by the current responsive phase until that phase is complete.

Conceptual phases:

- `desktop-rest`
- `desktop-to-phone`
- `phone-live-scroll`
- `phone-to-tablet`
- `tablet-live-scroll`
- `responsive-complete`

Forward wheel behavior:

- `desktop-rest` -> scrub / commit desktop-to-phone transformation
- `desktop-to-phone` -> continue toward phone-rest
- `phone-live-scroll` -> scroll content inside phone
- at phone handoff -> begin phone-to-tablet transformation
- `tablet-live-scroll` -> scroll content inside tablet
- `responsive-complete` -> next new deliberate gesture may advance the presentation

Reverse wheel behavior must undo the same sequence in reverse rather than jumping directly back to the previous presentation slide.

Invariant:

> While the responsive sequence has unfinished internal progress, wheel input changes that responsive sequence instead of changing presentation slides.

## Arrow / keyboard behavior

Visible presentation arrows and keyboard arrow keys must not contradict the wheel model.

Preferred behavior:

- During a device transformation, Down / Right advances to the next meaningful responsive phase.
- During a live device-scroll phase, Down / Right advances the internal device content by a controlled amount or to the next authored handoff point.
- Up / Left reverses correspondingly.
- Only after `responsive-complete` does Down / Right advance to the next presentation slide.

This preserves one navigation grammar even though Slide 03 contains more internal depth than a normal slide.

## Motion character

- Movement should feel continuous and physically related to the user's scroll input.
- Prefer scroll-scrubbed interpolation for device morphing rather than a completely automatic canned animation.
- The content and device frame may move at slightly different rates to create depth, but avoid exaggerated parallax.
- Device borders should emerge gradually from layout geometry; avoid a phone mockup suddenly popping around the content.
- The actual breakpoint/reflow should be perceivable, not hidden by blur or a full-screen transition effect.
- The presentation frame remains visually anchored throughout.

## What must not happen

- Do not replace the live website with static screenshots for each device.
- Do not merely `scale()` the desktop layout until it fits a phone.
- Do not let phone internal scrolling accidentally trigger the next presentation slide.
- Do not allow trackpad momentum to skip phone or tablet phases.
- Do not trap the viewer indefinitely inside the device demo; completion and exit must be visually understandable.
- Do not show a fake device frame if the content inside does not actually adapt.

## Reduced motion

For `prefers-reduced-motion`:

- Replace continuous morphing with short, clear state changes between desktop, phone, and tablet.
- Preserve the same live responsive layouts and internal device scrolling.
- Do not remove the ability to inspect all three responsive states.

## Proof condition

The scene succeeds only if the viewer can visually follow one continuous website through:

Desktop -> Phone reflow -> live phone scroll -> Tablet reflow -> live tablet scroll

without the experience feeling like three unrelated mockups.
