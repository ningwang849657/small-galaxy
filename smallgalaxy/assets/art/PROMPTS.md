# Rainforest residents — artwork provenance

Updated 2026-09-10. Generated with the built-in `image_gen` tool in reference-image/edit mode (not an external API or a CLI model). The previous `forest-sanctuary.webp`, `rainforest.webp`, and `rainforest-living.webp` are retained and are not overwritten.

## Delivered assets

| Asset | Role |
| --- | --- |
| [rainforest-canyon.webp](rainforest-canyon.webp) | Rainforest canyon and central river; preserves the previous right-hand tree |
| [forest-deer.webp](forest-deer.webp) | Forest Spirit, revealed by sunshine |
| [white-wolf.webp](white-wolf.webp) | White wolf, revealed by mist |
| [night-walker.webp](night-walker.webp) | Night Walker, revealed by downpour |

The generated PNGs were encoded to WebP with `ffmpeg -c:v libwebp -quality 88 -compression_level 6`, without resizing, cropping or manual retouching. All three character files have a real alpha channel, verified after encoding and again by the browser test. Earlier deer attempts with a baked-in checkerboard were rejected and are not included.

## Integration constraints

- Keep the current single canvas, editable copy, scene choices and weather timing.
- Anchor the Night Walker in the deepest forest, the deer on either middle riverbank, and the wolf only by the right-hand tree roots. Coordinates are in the painting's 1440×480 world, not the available UI space.
- Change deer banks on a new sunny appearance, not every frame. Resize only within these habitats to avoid text; never relocate a wolf to another part of the forest.
- As delivered, the painting put large foreground leaves at the requested wolf patch (84% across, 78% down) and no ground under them. The wolf therefore sits on the mossy shelf at the tree's foot, 67–76% across and about 77% down, which is the nearest real terrain. Coordinates in `dashboard-decor.js` follow the painting, not this brief.
- The deer's first choice is the ford in the foreground water directly below the play and loop buttons (x 296-330 and 470-508, y 424-434), alternating sides on each new sunny appearance. Seats at y >= 400 count as wading: the sprite's lower legs are masked into the water surface and the contact shadow is dropped. It never retreats upstream into the misty far water - at that distance there is no readable water surface under its hooves and it reads as floating. When the panel is too short for its head to clear the control row (more than 45% of its height would sit behind the buttons) it returns to the middle riverbanks instead.
- Solid controls (buttons, track chips) no longer push residents away - a resident may wade past behind them. Only text that floats directly on the painting keeps a clear space.
- A resident that cannot fit at 45% of its natural size stays away for that spell rather than appearing as a speck.
- The camera crop follows the layout only. It must never track whichever resident is out, or the whole painting slides sideways every time the weather turns.
- On narrow screens, raise the hero to 780 px and share an identical camera crop between the background and resident SVG. Pan to the active habitat and cap each resident at half the viewport width.
- Embed all four images in the generated HTML: no network requests for artwork.
- Keep the existing SVG silhouettes as a fallback for a missing asset.
- Weather remains an artistic simulation, not live weather data.

## Final prompt set

### rainforest-canyon.webp (current background)

Edit target: [rainforest-living.webp](rainforest-living.webp). Generated 2026-09-10, 2172×724 pixels. Characters remain separate transparent assets; the current background contains no baked-in residents.

```text
Use case: precise-object-edit.
Input image 1: EDIT TARGET, the current wide rainforest painting for a website. Edit this exact painting, not a new independent composition.
Primary request: preserve the large ancient tree on the RIGHT, its trunk, buttress roots, hanging vines, wet leaves, scale and location unchanged. Repaint ONLY the left and middle landscape as a lush tropical rainforest CANYON, with a clear jade river winding through its center from the distant interior toward the viewer.
Composition: keep the same panoramic 3:1 framing and the entire existing rightmost third, with absolutely no reframing or moving the large right tree. On the LEFT and center background introduce layered steep mossy limestone canyon sides clothed in rainforest, with soft humid mist separating distant trees and cliffs. A deep forest opening at roughly 53% across and 46% down is the vanishing point. The river comes forward from there in a gentle S curve, broadening through the central foreground, with visible rounded stones under clear water and modest shallow rapids. Give it natural walkable mossy stone banks at the middle left and middle right, around 43% and 66% across, 70% down. Keep the original right-tree buttress roots intact, and a small natural mossy resting patch directly at their base, around 84% across, 78% down. These are natural terrain, not platforms or stages.
Style: match the reference's detailed hand-painted animated-film background, realistic wet plant textures, delicate distant atmospheric perspective, quiet natural soft daylight. Retain the reference greens and cool pale mist. Make the canyon depth readable rather than filling everything with foliage.
Invariants: right-hand tree and its attached vines/leaves stay exactly as they are; same camera and 3:1 aspect; no animals, no deer, no wolf, no spirits, no giant, no people, no buildings, no text, no UI. The three characters are separate app layers and must NOT be painted into this background. Keep the top-left area softly misty so webpage text stays readable. No dramatic spotlight, no rainbow or rain streaks baked into the image.
```

### rainforest-living.webp (retained previous background)

Reference: [rainforest.webp](rainforest.webp).

```text
Use case: stylized-concept / realistic environment painting. Asset type: a single continuous 3:1 panoramic rainforest backdrop for an existing compact 1440x480 web dashboard canvas. Reference image is a style reference for its rich natural painted textures, not a composition to copy. Repaint an extraordinarily detailed Southeast Asian lowland tropical rainforest, intimate forest interior rather than a distant mountain valley: towering dipterocarp trees with buttress roots at the far right, rattan palms, glossy alocasia leaves, hanging fine vines, tiny ferns and moss on bark, damp smooth stones, a small clear dark-teal stream with exquisite soft reflections. Layered depth from sharply painted near leaves at the extreme lower corners to soft distant trunks and humid pale jade mist. Practical layout constraints: the UPPER THIRD across the whole width must remain soft and airy pale mist for a header row; LEFT HALF and central-left middle must be softly lit low-detail negative space for several dark text lines, NOT a blank white rectangle. Put most intricate foliage and bark in the RIGHT THIRD and LOWER QUARTER. Along the LOWER edge create a gently curved continuous mossy bank with a few clear natural resting spots, especially near 70% and 80% across, at about 90% down the image, where separately animated small animals will later stand. Do NOT draw any animals, spirits, faces or people in this backdrop. Natural seamless atmospheric transitions, no artificial split panels. Near-photorealistic botanical textures with hand-painted cinematic animation craft and rich jade/fern-green/cool-teal color separation, soft neutral diffuse daylight. Preserve microtexture and tactile depth; do NOT bake a white opacity wash over the whole image, the website controls opacity. No falling rain, lightning, sun disc, rainbow or hard sun shafts; the website renders weather dynamically. Wide approximately 2400x800 panorama. No text, UI, logos, border, watermark. One finished immersive environment, not a collage.
```

### forest-deer.webp

Reference: [forest-sanctuary.webp](forest-sanctuary.webp).

```text
A transparent-background cutout PNG of just the Forest Spirit deer from Princess Mononoke, whole body, on a genuinely transparent background. A small game sprite, not a scene. Graceful golden brown deer with branching gold antlers, ivory chest, shaggy fur, an elegant narrow face with red markings, standing in three-quarter view toward the left. Match the hand-painted deer in the reference's RIGHT third, with the same fine fur texture, natural anatomy, golden antlers and soft light. All four hooves and entire antlers visible, modest empty margin. No setting, no checker pattern, no white rectangle, no background colors. Deliver a PNG with the actual background removed, like a sticker cutout with a clean alpha channel. Portrait aspect ratio 3:4. Do not copy or use any scenery from the reference.
```

### white-wolf.webp

Reference: [forest-sanctuary.webp](forest-sanctuary.webp).

```text
Use case: stylized-concept. Asset type: a single transparent illustrated animal sprite for a small web rainforest habitat. Reference image is ONLY a style and identity reference: match the magnificent white wolf resting on the left, do not reproduce the backdrop. Draw one majestic white wolf inspired by Moro from Princess Mononoke, full body reclining peacefully facing right, head lifted alert, triangular upright ears, long natural muzzle, two visible front paws extended, rear haunch folded, a large relaxed fluffy tail along the body. Richly hand-painted fine ivory and pearl-white fur, pale moss-gray shadows, dark tiny attentive eyes and nose, believable canine anatomy and weight. Calm forest guardian, not a cute domestic dog and not an angry snarl. Cinematic animation background painting quality like the reference, softly shaded volume. Clear elegant silhouette legible when displayed only 100px wide. Landscape composition approximately 1024x768, subject centered occupying 88% width with ALL paws, ears and tail intact. Genuinely TRANSPARENT RGBA background with clean antialiased edges, no painted checkerboard, no environment, rock, grass, text, border, watermark or other character. Only an extremely subtle soft contact shadow directly beneath the reclining body.
```

### night-walker.webp

Reference: [forest-sanctuary.webp](forest-sanctuary.webp).

```text
Use case: stylized-concept. Asset type: a single isolated transparent character sprite for a small web rainforest habitat. Reference image is a PAINTING STYLE reference only, not the requested character. Draw the Night Walker / Daidarabotchi, the nocturnal form of the Forest Spirit from Princess Mononoke, one full-body ethereal forest giant. Tall elongated humanoid silhouette, long graceful arms ending in hands at the thighs, long legs, rounded mystical face with tiny luminous eyes, an intricate broad crown of tree-like branching antlers. Body made of translucent midnight cobalt, teal and pale cyan luminous organic matter, filled with fine silver-blue starlight and flowing nebula-like internal texture. Soft turquoise luminous edge, subtle semi-transparent skin, elegant and mysterious, gentle rather than frightening. Pose quietly upright with a slight walking weight shift, full feet visible, face three-quarter view toward left. Hand-painted cinematic animation detail consistent with the reference, not 3D plastic, not flat icon, not a bulky superhero, no clothing. Needs a recognizable readable silhouette at about 125px tall, more substantial body than thin stick figure. Portrait composition approximately 768x1024, entire antlers and feet inside the frame with 5% breathing room. Genuinely TRANSPARENT RGBA background, retain translucent edge glow and fine antler branches; no sky, environment, grass, ground plane, checkerboard texture, text, logos, watermarks or other characters.
```
