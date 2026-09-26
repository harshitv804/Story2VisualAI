# SCENE → SUB-SCENE EXTRACTION

## ROLE
Split the current scene into the **minimum number of coherent visual sub-scenes** for key-story images — not shot-by-shot coverage. No camera angles, close-ups, wide shots, or alternate compositions as separate sub-scenes.

## INPUT
```text
Previous scene:
{{PREV_SCENE}}

Current scene:
{{CURRENT_SCENE}}
```
- `prev_scene` (`{"scene_id": "...", "scene_desc": "..."}`) is **reference/continuity only**.
- `current_scene` is the scene to analyze and split.
- If no previous scene is provided, treat the current scene as the first scene of the story.

## OUTPUT
Valid JSON only — no markdown, explanation, or analysis:

```json
{
  "subscenes": [
    {"scene_id": "S2A", "scene_desc": ""}
  ]
}
```

One major visual/story beat → one sub-scene. Typical scene → **1–3 sub-scenes**; exceed 3 only when several major transitions clearly occur. No transition → exactly one sub-scene. Chronological order.

## SPLIT WHEN
1. **Different time** — night → morning.
2. **Major action** — sleeping → waking, when it creates a substantially different visual state (not every small movement).
3. **Transformation / major physical change** — human → monstrous insect.
4. **Location change** — bedroom → hallway.
5. **New character/event** — alone → family enters, when it creates a meaningful new visual/story situation.
6. **Important emotional/story beat** — confusion → realization; calm → confrontation, only when visually strong enough to be a distinct key image.
7. **Significant environmental/narrative change** — quiet room → sudden disturbance; normal → important discovery.

## DO NOT SPLIT FOR
Minor movements, small gestures, individual sentences, individual dialogue lines, speaker changes, looking at something, walking a few steps, minor emotional fluctuations, small actions within the same visual situation, camera-angle or framing changes, close-up vs. wide, or repeated descriptions of the same situation. Example: *looks toward the clock → reaches toward it → struggles to read it* = **one sub-scene** if it is one continuous visual moment.

## CONTINUITY
Use `prev_scene` to know what already happened; it is context, not content to repeat.
- Ask: what visual/story state exists at the end of the previous scene? What new information begins in the current scene? Does it continue the same situation or meaningfully change?
- Do not create a sub-scene merely because prior information is mentioned again.
- If the current scene continues then transitions into a major new event, split at that transition.
- The first sub-scene should connect naturally to the previous scene. Do not invent a transformation sub-scene if the current scene is primarily a continuation of that state.

## SUB-SCENE DESCRIPTION
Concise, concrete, visually understandable, self-contained, useful for image generation — what is visibly happening, not literary interpretation.
- Good: `"Gregor Samsa lies trapped on his hard arched back in his small bedroom, his numerous thin legs moving helplessly as he struggles to reach the alarm clock."`
- Avoid: `"Gregor experiences profound existential despair as he confronts the absurdity of his transformed existence."`
- Use the known character's actual name — never he/she/they/him/her/them/his/their when the name is known.
- No character IDs, prop IDs, world IDs, or other metadata.
- Invent nothing: no new characters, locations, actions, objects, weather, time periods, events, transformations, or developments. Reasonable visual wording is allowed, but the actual event must come from the input.

## IDS
All sub-scene IDs use the **current** scene ID as base: current `S2` → `S2A`, `S2B`, `S2C`. Never use the previous scene's ID.

## TEST
Ask: *can all these events reasonably be represented by one coherent generated image?* Yes → keep together. No, due to a substantial visual/story transition → split.

## EXAMPLE
Previous: `S1` = *Gregor Samsa goes to sleep in his bedroom in his ordinary human form.*
Current: `S2` = *The following morning Gregor Samsa wakes up transformed into a monstrous verminous bug. Later, Gregor struggles to get out of bed and reaches toward the alarm clock showing nearly seven o'clock.*

```json
{
  "subscenes": [
    {"scene_id": "S2A", "scene_desc": "Gregor Samsa wakes up in his bedroom transformed into a monstrous verminous bug, lying helplessly on his hard arched back with numerous thin legs wriggling in the air."},
    {"scene_id": "S2B", "scene_desc": "Gregor Samsa remains trapped on his back in his bedroom and struggles toward the alarm clock, which shows nearly seven o'clock."}
  ]
}
```
Do not split into *wakes up / looks at legs / realizes he is a bug* — same beat. A transformation-only scene yields exactly `S2A`.

## FINAL CHECK (internal)
1. Inherited state from `prev_scene` identified; new current-scene events identified.
2. Only major visual/story transitions split; minor actions, camera angles, and dialogue not split.
3. Nothing invented; each sub-scene self-contained with explicit names.
4. All IDs use the current scene ID; chronological order.
5. Fewest sub-scenes that cover the beats; valid JSON only.

Generate the sub-scenes now.
