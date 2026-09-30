# CINEMATIC ANIME ENVIRONMENT REFERENCE PROMPT

Role: write ONE affirmative image-generation prompt for the canonical BASE REFERENCE image of the location in {{WORLD_META}}, in the anime treatment of {{STORY_STYLE}}. Output = reusable ENVIRONMENT ASSET, not a story moment, not a character shot.

## RULES
1. Medium is always anime. Never live-action, photoreal, 3D, Pixar, claymation, western comic, architectural render. {STORY_STYLE} sets only the anime sub-treatment: line quality, shading, palette, warmth, realism level, period aesthetic, texture rendering.
2. world_desc is canon. Preserve architectural type, scale, layout, materials, colors, era, named objects, condition, fixed openings (doors, windows, ledges). Infer only small gaps from implied function, period, and culture, nothing decorative or invented.
3. Composition = neutral establishing view: full space in frame, all key elements visible edge to edge, majority of frame clear, natural undistorted eye-level or slightly elevated perspective, level horizon, straight-on or gentle three-quarter. No dramatic framing.
4. Space is vacant and undisturbed: every surface untouched, every door in its resting position, every object in its settled place.
5. Atmosphere = standing condition only (dusty, neglected, pristine, opulent, cozy), never a plot event such as fire, struggle, or fresh damage.
6. Lighting soft, even, diffused. Style may shift warmth and softness, never turn it into a dramatized moment.
7. Positive-only phrasing: describe what IS present, zero negation tokens (no, not, without, avoid, excluding, free of, absent), no negative-prompt section. Rewrite each exclusion affirmatively:
   - empty space -> "a quiet, empty interior, completely vacant of occupants, every surface left undisturbed"
   - blank backdrop -> "seamless solid white studio backdrop filling the entire frame"
   - uncropped set -> "the complete room fully within frame, all walls, furniture, fixtures visible edge to edge"
   - undistorted view -> "a level, eye-height, undistorted straight-on architectural perspective"
   - still moment -> "a still, calm, undisturbed environment in a quiet neutral moment"
   - clean surfaces -> "a clean surface rendered as pure environmental texture"
8. Priority: location identity and function, then layout and scale, then furniture and structure, then materials and palette, then set-dressing, then condition, then anime style, then period aesthetic, then clean reference presentation. Cinematic style never overrides location identity.
9. Output only the prompt: exactly {"image_prompt": "<prompt>"} and nothing else. No headings, metadata, analysis, explanation, or variants inside the prompt text.

## SLOT SEQUENCE (fill in order, each bracket = concrete world info)
1. `Anime environment reference of [name],`
2. `wide establishing view, complete space visible,`
3. `[architectural type and scale],`
4. `[layout and key structural elements],`
5. `[defining furniture and objects],`
6. `[materials, colors, decor],`
7. `[atmosphere / standing condition],`
8. `[anime treatment from story_style],`
9. `[period aesthetic from story_style],`
10. `soft even diffused lighting,`
11. `a quiet, empty interior completely vacant of occupants, every surface undisturbed,`
12. `clean uncluttered presentation,`
13. `centered legible composition, entire location visible from edge to edge,`
14. `high environmental-detail consistency, professional environment concept reference aesthetic`

## CHECK BEFORE RETURNING
- Anime medium, treatment reflects story_style.
- Every named world_desc element present, unobstructed, complete.
- Space whole, vacant, neutral perspective, standing condition.
- Zero negation words, no negative section, no extra sections.
- One continuous affirmative block reusable as a canonical location reference.

## INPUT
world: {{WORLD_META}}
story_style: {{STORY_STYLE}}
