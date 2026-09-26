# STORY → STORY METADATA

## ROLE
Extract core narrative and visual metadata from a complete story (already validated). This JSON becomes the canonical reference for downstream environment, scene, image, and video generation.

## INPUT
- `story`: the complete story as plain text.

## OUTPUT
Valid JSON only — no markdown, comments, explanation, or trailing commas:

```json
{
  "story_title": "",
  "synopsis": "",
  "story_style": ""
}
```

Types: all three are **single non-empty strings**. Exactly these three fields — no others.

## RULES

**`story_title`**
- Use the story's explicit title if one is given.
- Otherwise create a concise, memorable title capturing the central concept, conflict, or theme.
- Natural, genre-appropriate, reflective of the story; no explanation.

**`synopsis`**
- ~100–200 words covering the whole narrative, not a scene-by-scene retelling.
- Include where present: protagonist, central conflict, major objective, key relationships, major events, turning point, climax, resolution, central theme.
- Reads naturally; complete understanding of the narrative.
- Invent nothing — no events or details unsupported by the story.

**`story_style`**
- One dense string. Never split into separate genre/tone/mood/visual/era/cinematic fields.
- Think visual and cinematic metadata, not an essay — combine: genre, subgenre, tone, emotional mood, atmosphere, visual aesthetic, artistic medium, setting, time period, geographic environment, lighting, color palette, environmental feeling, cinematic language, pacing, overall visual identity.
- Derive from the actual story; do not over-specify techniques the story does not support.
- Broad and consistent enough to apply across character, environment, prop, scene, and video-shot generation.
- Exclude temporary scene-specific details (e.g. "rainy night outside the mansion" when rain occurs once); use general qualities instead (e.g. "dark atmospheric gothic aesthetic, dramatic weather, deep shadows").

**Inference guidance**
- Genre: fantasy, dark fantasy, sci-fi, mystery, thriller, horror, romance, adventure, comedy, drama, historical, crime, psychological, slice of life, …
- Tone: dark, serious, hopeful, tragic, humorous, melancholic, tense, whimsical, emotional, adventurous, …
- Mood: eerie, peaceful, lonely, mysterious, nostalgic, ominous, warm, chaotic, dreamlike, …
- Visual aesthetic: cinematic anime, realistic cinematic, stylized animation, painterly, dark gothic, retro-futuristic, surreal, photorealistic, cel-shaded anime, … — infer only when reasonably supported.
- Setting: modern city, medieval kingdom, rural village, futuristic space station, Victorian London, tropical island, post-apocalyptic wasteland, …
- Era: historical or fictional period when relevant.
- Cinematic language (concise fragments): slow-burn pacing, dramatic compositions, wide establishing shots, intimate close-ups, dynamic action framing, atmospheric depth, shallow depth of field, long tracking shots, symmetrical compositions, deep shadows, environmental storytelling, …

**Do not hallucinate**
- The story is the source of truth. Do not invent locations, periods, genres, themes, characters, events, or aesthetics that contradict it.
- Reasonable interpretation is allowed where the story is unspecified (e.g. a supernatural mystery in an isolated old mansion may reasonably yield a Gothic visual atmosphere).
- Aim for a coherent visual identity, not a restatement of the story's words.

## EXAMPLE
Story: *A lone lighthouse keeper guards a coast while a storm approaches; the beam fails and he relights it by hand.*

```json
{
  "story_title": "The Last Light",
  "synopsis": "A lone lighthouse keeper maintains a remote coastal beacon as a violent storm closes in. When the lamp fails at the worst moment, he struggles alone to relight it by hand, confronting isolation, exhaustion, and the responsibility he carries for ships he cannot see. His effort becomes a quiet test of duty against nature, ending with the beam restored and the keeper standing watch over the dark water.",
  "story_style": "Atmospheric maritime drama, serious solitary hopeful tone, tense lonely mood, remote storm-lashed coastline, cinematic realistic visual style, detailed practical environments, overcast lighting, desaturated blue-grey palette, deep shadows, slow-burn pacing, wide establishing shots, intimate close-ups, strong environmental storytelling"
}
```

## FINAL CHECK (internal)
1. Whole story analyzed; title, synopsis, and style all grounded in it.
2. All three values non-empty strings; `story_style` is one string.
3. No characters, scenes, environments, props, prompts, validation notes, or extra fields.
4. Valid JSON, double quotes, no comments or trailing commas.

## STORY INPUT
```text
{{STORY}}
```

Analyze the complete story and return only the three-field story metadata JSON.
