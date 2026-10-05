# Character → Base Reference Image Prompt

Your task: generate ONE image-generation prompt for the **canonical base reference image** of a character — a reusable, stable anime character-sheet asset for later scene-generation workflows, never a story scene.

Given the fields `character` (`{{CHAR_META}}` — `name`, `role`, `char_desc`), `story_style` (`{{STORY_STYLE}}`), and `synopsis` (`{{SYNOPSIS}}` — context only), produce the field `image_prompt`.

## Output Field
`image_prompt` = a single block of purely positive, affirmative descriptive text, directly usable by Flux 2 Klean. Output ONLY the prompt — no JSON, no headings, no analysis, no negative-prompt section.

## Rules

1. **Medium is always anime.** Hand-drawn anime/manga: flat cel shading, clean linework, stylized anime proportions and facial features. Let `story_style` tune only the rendering treatment — e.g. dark crime → mature cinematic anime, restrained linework, realistic proportions; fantasy → expressive eyes, elaborate rendering; period → muted palette, delicate linework; modern action → sharper linework, strong cel shading. Anime stays the underlying medium regardless of genre.

2. **Identity = `char_desc`.** Preserve every stated attribute exactly: age, gender, build, proportions, face shape, eye color, hair, skin tone, facial hair, scars/tattoos, canonical clothing, defining accessories. Fill genuine gaps minimally from role, occupation, synopsis, period, and setting — coherent canon, minimal invention.

3. **Composition: full-body head-to-toe reference pose.** Head, hair, shoulders, arms, hands, torso, legs, and feet all fully visible; the entire figure centered with clean space around the silhouette. Upright standing, relaxed shoulders, arms resting at the sides or slightly apart, hands open and empty, weight balanced, facing the viewer. Natural eye-level straight-on or slight three-quarter view, standard undistorted lens, true-to-life proportions.

4. **Expression & condition.** A calm baseline expression matching the character's settled personality (permanent defining traits only, never a plot-moment emotion). Canonical everyday clothing in pristine, settled condition — fully visible, clearly rendered, period-appropriate. Accessories limited to those canonically named, kept recognizable.

5. **Background, lighting, isolation.** A completely bare, seamless pure white studio backdrop filling the entire frame; the character evenly and brightly lit from all sides, floating gently just above the white surface, blending seamlessly into it at the point of contact. A single solitary figure, cleanly isolated, occupying most of the vertical frame. Soft, even, neutral studio lighting preserving the face, skin/hair colors, clothing details, and silhouette — a calm character-sheet presentation, never a cinematic scene.

6. **Positive-only phrasing.** Describe only what IS present, being fully explicit so nothing is left to exclude. Never use "no", "not", "without", "avoid", "excluding", "free of", "absent of". Translate exclusions affirmatively: → "a completely bare, seamless pure white studio backdrop"; → "a single solitary character standing alone, the only figure present"; → "the entire figure shown fully in frame, from the crown of the head to the soles of both feet"; → "evenly and brightly lit, blending seamlessly into the white surface".

## Prompt order (replace slots with real content)
Anime character reference portrait of [NAME] → full-body head-to-toe view → canonical physical appearance → face & hair → distinctive features → canonical clothing → canonical accessories → personality-consistent neutral expression → neutral reference pose → anime style derived from story_style → period aesthetic → soft even studio lighting → clean silhouette → pure white seamless background → isolated solitary figure → centered composition → entire figure fully visible head to toe → high character-detail consistency → professional character reference sheet aesthetic.

## Self-check before output
Anime medium, treatment reflects `story_style`, matches `char_desc`, full-body incl. feet, face clear, neutral pose & identity-consistent expression, canonical clothing & accessories, seamless pure white backdrop, solitary figure, everyday condition, zero negation words anywhere, one reusable prompt only.

## Input
```text
character:
{{CHAR_META}}

story_style:
{{STORY_STYLE}}

synopsis:
{{SYNOPSIS}}
```

Generate the final `image_prompt` now.