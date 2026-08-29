# ARC 01 — Image-led Web Design

Status: design direction locked for the next implementation pass.

This note defines how the approved ARC 01 master product photograph should drive the shared VELLUM product website used in Slide 02 and Slide 03.

`STORYBOARD.md` remains the master presentation plan. `SHARED_PRODUCT_BRIEF.md` remains the content source. `SLIDE_02_VISUAL_RANGE.md` remains the four-style intent. This note defines the concrete image-led art direction.

## Master image

Use the approved ARC 01 hero photograph from the current design session as the shared visual source.

Expected implementation asset path:

`website-presentation/assets/arc01-master.png`

The image has these useful compositional properties:

- tall black arched lamp occupying the right side,
- warm illuminated wall behind the lamp,
- large quiet cream / warm-gray negative space through the center and upper-left,
- cropped sculptural lounge chair in the lower-left,
- small side table creating believable scale without competing with the lamp,
- warm pale wood floor,
- strong vertical crop tolerance.

Do not replace this photograph with a different lamp per theme.

Theme changes may use different crops, masks, overlays, exposure treatments, and scale, but the same underlying photograph must remain identifiable.

## Shared page anatomy

All four Slide 02 styles use the same content nodes.

1. Brand: `VELLUM`
2. Navigation: `Objects / Journal / About / Cart 0`
3. Category: `OBJECTS / LIGHTING`
4. Product: `ARC 01`
5. Headline: `빛을 낮게, 공간을 깊게.`
6. Description from `SHARED_PRODUCT_BRIEF.md`
7. Price: `₩348,000`
8. Primary CTA: `제품 보기`
9. Secondary action: `빛 켜보기`
10. Product facts
11. One shared ARC 01 photograph

No extra marketing sections are required for Slide 02. The one-screen composition itself is the demonstration.

## Style 01 — Editorial / Luxury

### Composition

- Warm ivory page surface close to the photograph's wall tone.
- Photograph occupies roughly the right 52–58% of the demo canvas as a tall edge-to-edge image field.
- Preserve the lamp's full base-to-arc silhouette whenever possible.
- Left side remains quiet and text-led.
- `ARC 01` is small-to-medium metadata; the Korean headline is the dominant typographic statement.
- Description and price sit low and understated.
- CTA behaves like refined editorial text / thin-rule control rather than a heavy commerce button.
- Product facts appear as very small aligned metadata near the bottom edge.

### Typography

- Editorial serif for the headline.
- Neutral sans-serif for navigation and metadata.
- High contrast between expressive headline and restrained supporting information.

### Image treatment

- Natural color photograph.
- No obvious filter.
- Very subtle warm tonal integration with the page background.
- The photograph should feel like commissioned art direction, not a card pasted into a layout.

### Intended impression

Quiet premium furniture / lighting editorial.

## Style 02 — Swiss / Functional

### Composition

- Hard white / off-white surface.
- Visible modular grid.
- Photograph becomes a strict vertical module occupying about 5 of 12 columns on the right.
- The same photograph is cropped more tightly around the lamp and lower furniture edge.
- Product name, price, dimensions, material, and actions become explicit information blocks.
- Headline remains unchanged but becomes a structured text block rather than a poetic hero statement.
- Specs move from quiet footer metadata into the visible grid.

### Typography

- Sans-serif only.
- Strong weight contrast.
- Uppercase metadata.
- Tabular alignment for price / product facts where practical.

### Accent

- One assertive signal color, preferably red / vermilion.
- Use only for active state, rules, or one CTA marker.

### Image treatment

- Natural photograph with slightly cleaner / more neutral contrast.
- No decorative frame radius.
- Crop should feel intentional and architectural.

### Intended impression

Precise catalogue / industrial design system.

## Style 03 — Playful / Expressive

### Composition

- Strong flat background color outside the photograph.
- Recommended base: saturated cobalt or vermilion; exact value can be tuned in implementation.
- The photograph becomes an oversized vertical slab or off-grid crop rather than a conventional hero card.
- Keep the lamp readable; do not rotate or distort the actual photograph enough to break product recognition.
- Headline becomes oversized graphic typography and may overlap the photograph boundary.
- Price and CTA become bold graphic anchors.
- Specs remain present but can be arranged as smaller typographic stamps.

### Typography

- Heavy sans-serif.
- Very large Korean headline.
- Intentional line breaks and scale shifts.
- Avoid rounded SaaS-pill styling as the main device.

### Image treatment

- Keep the source image recognizable.
- A mild color wash / multiply / screen overlay is allowed, but do not reduce the photo to an unrecognizable duotone.
- The warm lamp light should remain visible because it is the visual bridge to Style 04.

### Intended impression

Confident contemporary poster / campaign website.

## Style 04 — Cinematic / Immersive

### Composition

- The photograph becomes full-bleed across the entire product website.
- Use the existing dark lamp silhouette and warm wall glow as the visual center.
- Add a controlled dark gradient only where required for text legibility.
- Brand / navigation remain small and quiet at the top.
- Product information sits primarily in the lower-left negative-space region.
- Price / CTA can sit lower-right or align with the lamp base depending on the crop.
- Specs become a thin bottom information rail or reveal on interaction.

### Typography

- Minimal text count.
- Warm white / soft ivory.
- Product name and headline remain clearly readable but do not compete with the photograph.

### Image treatment

- Full photographic depth.
- Slightly deeper blacks and controlled warm highlights.
- No fake neon bloom.
- The actual lamp glow is the scene's light source.

### Intended impression

High-end architectural / furniture campaign site.

## Theme transformation choreography

The image is the continuity anchor across all four themes.

### Style 01 -> Style 02

- Right-side photo field narrows and snaps toward the grid module.
- Serif headline reorganizes into a functional text block.
- Quiet bottom metadata rises into explicit grid rows.
- Background cleans toward white.
- Signal accent appears late in the transition.

### Style 02 -> Style 03

- Grid lines release / recede.
- Photo module grows and moves off-grid.
- Headline rapidly gains scale and becomes a graphic layer.
- Flat campaign color takes over the page background.
- Price / CTA enlarge and reposition as visual anchors.

### Style 03 -> Style 04

- Photograph expands until it occupies the entire viewport.
- Flat color exits around the edges rather than crossfading to an unrelated scene.
- Oversized typography reduces in scale and moves into the lower-left composition.
- Supporting metadata becomes quieter.
- The warm lamp light becomes increasingly dominant.

The viewer should always be able to visually track the same photo through these moves.

## Slide 02 -> Slide 03 handoff

Style 04 is also the responsive site's desktop starting state.

Do not load a new page when Slide 03 begins.

Instead:

1. the full-bleed cinematic page receives a subtle browser / viewport boundary,
2. the page pulls back from the presentation stage,
3. its available width begins to contract,
4. responsive layout rules reflow the same VELLUM content,
5. the same ARC 01 photograph remains visible throughout.

## Responsive image behavior

### Desktop

- Full-bleed or near-full-bleed photograph.
- Text overlays the left / lower-left negative space.
- Specs remain compact.

### Phone

- Photo becomes the upper visual section of the product page.
- Use a tall crop preserving the lamp arc and upright.
- Product title / copy / price / CTA stack below or partially overlap the image edge.
- Internal phone content scroll is continuous, not checkpointed.

### Tablet

- Use a two-zone composition.
- Photograph occupies roughly 55–60%.
- Product information sits in a structured side panel / lower side region.
- Internal tablet content scroll remains continuous.

## Interaction rules

- Slide 02 style states are checkpoints.
- Desktop -> Phone and Phone -> Tablet transformations are checkpoints / authored transitions.
- Phone internal page scrolling is continuous.
- Tablet internal page scrolling is continuous.
- Reaching the end of an internal scroll does not immediately trigger the next checkpoint on the same momentum gesture.
- Slide 05 Retro / Legacy remains the deliberate hard / stepped motion exception.

## Failure conditions

Rework if:

- the photograph appears to be four different products,
- the photo is reduced to a small generic card in every theme,
- Style 02, 03, and 04 are mostly recolors of Style 01,
- the lamp silhouette is lost in mobile crops,
- the chair / side table become more visually important than the lamp,
- Style 04 cannot naturally contract into the responsive demo,
- theme transitions hide the continuity of the shared photograph.
