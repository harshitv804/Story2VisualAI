# STORY → SCENE METADATA

## TASK
Segment an entire story into chronologically ordered, visually coherent scenes. Return **only** scene metadata JSON.

## INPUT
- `story`: the complete story as plain text.

## OUTPUT
Valid JSON only — no markdown fences, no prose, no comments, no trailing commas:

```json
{"scenes": [{"scene_id": "S1", "scene_desc": ""}]}
```

## RULES

**Segmentation**
- Read the whole story first, then choose boundaries.
- Start a new scene only when location, time, major action, character activity, narrative situation, visual composition, or a significant event/transition changes enough to need a different shot.
- Never split per sentence, per dialogue line, or because the speaker changes; keep a continuous conversation in one scene.
- Split a dialogue-heavy scene only on a real visual/narrative change (location shift, time jump, major event).
- Never emit one giant scene, and never one scene per beat. Test: if the same image could serve before and after, it is the same scene.
- Order scenes strictly by narrative chronology; do not reorder or group by character or location.
- Cover the entire story: `S1` = opening, `Sn` = ending/resolution. Do not omit transitions, developments, climax, or resolution.

**`scene_id`**
- Sequential: `S1`, `S2`, `S3`, … No gaps, no reuse.

**`scene_desc`**
- One compact, concrete, present-tense visual description: who is present, what they do, key actions/interactions, action-relevant objects, environment, visible emotional/physical state, notable change, explicit temporal cues.
- Self-contained: fully understandable with no other scene as context.
- Use the exact story name for every visible or active character. No pronouns (he, she, they, him, her, them, his, their) and no generic labels (the man, the girl, the group, the mother, the detective, …) when the name is known. Resolve pronouns from full-story context.
- Keep names exactly as given — no renaming, abbreviating, or inventing. If a character is genuinely unnamed, use the most specific descriptive reference available.
- Visual, not literary: no interior monologue, mood prose, or figurative narration.
- No dialogue or quotable text: no speech, quotes, narration lines, subtitles, captions, or written text. Mention a physical note/letter/sign only as an object when it is visually relevant.
- Invent nothing (locations, characters, props, weather, time of day, costumes, eras, effects); allow only reasonable visual interpretation needed for clarity.
- No asset grounding: no character/prop/world IDs or fields, no camera directions, no image/video prompts. Names and objects may appear naturally inside `scene_desc` only.

**Final check (each scene)**
1. Every character reference uses the known name.
2. Scene stands alone.
3. No dialogue, IDs, or non-visual content.
4. IDs sequential, order chronological, story fully covered.

## EXAMPLE
Story: *Maya waits on the platform at dusk. A train approaches and she boards. Hours later she steps off in the city at night.*

```json
{"scenes": [{"scene_id": "S1", "scene_desc": "Maya stands beside the abandoned railway platform at dusk, waiting anxiously as a distant train approaches."}, {"scene_id": "S2", "scene_desc": "Maya steps off the train into a crowded city station at night."}]}
```

## STORY
```text
{{STORY}}
```

Generate the scene metadata JSON now.
