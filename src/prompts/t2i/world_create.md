# Signature

**Inputs**
- `world`: canonical location metadata (`world_id`, `name`, `world_desc`) extracted from the story.
- `story_style`: overall visual/cinematic style of the story.

**Output**
- `image_prompt`: one single block of affirmative descriptive text, directly usable as a Flux 2 Klean prompt.

---

# Task

Generate one image-generation prompt for the **canonical base reference image** of the location in `{{WORLD_META}}`, rendered in the anime treatment implied by `{{STORY_STYLE}}`. The image is a reusable **environment asset**, not a story moment and not a character shot.

---

# Rules

1. **Medium is always anime.** Never live-action, photorealistic, 3D, Pixar, claymation, western comic, or architectural render. Let `story_style` set only the anime sub-treatment: line quality, shading, palette, warmth, realism level, period aesthetic, texture rendering.
2. **`world_desc` is canon.** Preserve architectural type, scale, layout, materials, colors, era, named objects, condition, and fixed openings (doors, windows, ledges). Infer only small gaps from implied function, period, and culture — nothing decorative or invented.
3. **Composition is a neutral establishing view.** Full space inside the frame, all key elements visible edge to edge, majority of the frame clear, natural undistorted eye-level or slightly elevated perspective, level horizon, straight-on or gentle three-quarter orientation. No dramatic framing.
4. **Space is vacant and undisturbed.** Every surface untouched, every door in its resting position, every object in its settled place.
5. **Atmosphere is standing condition only** (dusty, neglected, pristine, opulent, cozy) — never a plot event such as fire, struggle, or fresh damage.
6. **Lighting is soft, even, and diffused.** Style may adjust its warmth and softness; it may not turn the image into a dramatized moment.
7. **Positive-only phrasing.** Describe what IS present. Use zero negation tokens (`no`, `not`, `without`, `avoid`, `excluding`, `free of`, `absent`). No negative-prompt section. Convert each exclusion into a complete affirmative description:

   | Exclusion | Affirmative rewrite |
   |---|---|
   | no characters | a quiet, empty interior, completely vacant of occupants, every surface left undisturbed |
   | no background scenery | seamless solid white studio backdrop filling the entire frame |
   | no cropped furniture | the complete room fully within frame, all walls, furniture, and fixtures visible edge to edge |
   | no fisheye / Dutch angle | a level, eye-height, undistorted straight-on architectural perspective |
   | no narrative event | a still, calm, undisturbed environment in a quiet neutral moment |
   | no text / watermark | a clean surface rendered as pure environmental texture |

8. **Priority order:** location identity and function → layout and scale → furniture and structural elements → materials and palette → set-dressing objects → condition → anime style → period aesthetic → clean reference presentation. Cinematic style never overrides location identity.
9. **Output only the prompt.** No JSON, headings, metadata, analysis, explanation, or multiple variants.

---

# Prompt Skeleton

Fill this sequence in order; every bracket becomes concrete world information.

| # | Slot |
|---|---|
| 1 | `Anime environment reference of [name],` |
| 2 | `wide establishing view, complete space visible,` |
| 3 | `[architectural type and scale],` |
| 4 | `[layout and key structural elements],` |
| 5 | `[defining furniture and objects],` |
| 6 | `[materials, colors, decor],` |
| 7 | `[atmosphere / standing condition],` |
| 8 | `[anime treatment derived from story_style],` |
| 9 | `[period aesthetic derived from story_style],` |
| 10 | `soft even diffused lighting,` |
| 11 | `a quiet, empty interior completely vacant of occupants, every surface undisturbed,` |
| 12 | `clean uncluttered presentation,` |
| 13 | `centered legible composition, entire location visible from edge to edge,` |
| 14 | `high environmental-detail consistency, professional environment concept reference aesthetic` |

---

# Verify Before Returning

- Medium is anime and its treatment reflects `story_style`.
- Every named element of `world_desc` appears, unobstructed and complete.
- Space is whole, vacant, and shown from a neutral perspective in its standing condition.
- Zero negation words; no negative-prompt section; no extra sections at all.
- Output is a single continuous affirmative block, reusable as a canonical location reference.

---

# Input

```text
world:
{{WORLD_META}}

story_style:
{{STORY_STYLE}}
