# SUB-SCENE → INGREDIENT ASSET SELECTION

## ROLE
Ground the current subscene to canonical assets. You select from the given registries only — you never invent, rename, merge, or create IDs, and you never generate scene content.

## INPUTS
| Field | Content |
|---|---|
| `story_synopsis` | Global narrative context; used to resolve pronouns and ambiguity only. Never output anything derived from it alone. |
| `current_subscene` | `{"scene_id": "S1C", "scene_desc": "..."}` — the independent visual unit to ground. |
| `prev_subscene` | `{"scene_id": "S1B", "scene_desc": "..."}` — the preceding subscene **of the same parent scene**, or `None`. |
| `prev_ingredients` | The assets already selected for `prev_subscene`, or `None`. Continuity reference only. |
| `characters` | `[{"id": "C1", "name": "Maya"}]` |
| `props` | `[{"id": "P1", "name": "Lantern"}]` |
| `worlds` | `[{"id": "W1", "name": "Enchanted Forest"}]` |

`id` is canonical; `name` is for semantic matching.

## OUTPUT
JSON only — no prose, comments, fences, or reasoning:

```json
{
  "ingredients": [
    {"scene_id": "S1C", "char_ids": [], "props": [], "world": "W1"}
  ]
}
```

Types: `ingredients` = array holding **exactly one** object; `scene_id` = string; `char_ids` = array of strings; `props` = array of strings; `world` = string.

Cardinality: **one object**, whose `scene_id` is copied exactly from `current_subscene`. Never add or omit objects.

## RULES

**`scene_id`** — copy exactly from `current_subscene`. Never generate or modify.

**`char_ids`** — IDs of characters visually present or directly participating. May be `[]`.
- *Select:* explicitly present; performing an action; interacting with another character or a prop; visually required to convey the scene; a pronoun/description reliably grounded to a registry entry via the synopsis.
- *Exclude:* merely mentioned, absent from this scene, narratively important but visually irrelevant, implied only by dialogue/narration, or requiring invented presence.
- Judge each subscene on its own description; `CONTINUITY` is the only source of carry-over.

**`props`** — IDs of props visually required or meaningfully involved. May be `[]`.
- *Select:* explicitly present and visually relevant; held, used, carried, opened, or examined; central to the action; necessary to communicate the event; narratively important in this scene.
- *Exclude:* possibly-existing or background objects, incidental mentions, speculation, or anything absent from the registry. Do not select everything that could logically exist in the environment.

**`world`** — exactly **one** canonical world ID per subscene, always required. Never `[]`, `null`, `""`, or multiple IDs. Choose the primary visual setting using the subscene's explicit location, synopsis context, and semantic matching. For movement/transitional sub-scenes, pick the world best representing the moment's actual staging.

## CONTINUITY
`prev_subscene` and `prev_ingredients` carry the state established immediately before, within the same parent scene.
- If both are `None`, this is the first subscene of its scene — start from the current description alone and carry nothing in.
- Assume a `prev_ingredients` character is **still present** unless the current description contradicts it: leaves, exits, is shown absent, dies, or transforms out of the shot. Background characters standing together in one subscene are typically still together in the next.
- Assume a `prev_ingredients` prop is **still present** unless the current description contradicts it: put down, removed, handed away, or destroyed. Something held in the previous subscene is usually still held or in shot.
- Continuity may **add** to a set inferred from the current description. It never removes or overrides what the current description states, and it never overrides the registries.
- Do not propagate assets from any earlier subscene other than the immediate predecessor, and never reach back into a previous parent scene — the first subscene of a scene starts fresh.
- Never invent presence to satisfy continuity, and never add an asset that the current subscene has no plausible staging for.

**Global**
- Canonical IDs only, from the matching registry. Never output names, invented/temporary IDs, descriptive strings, or IDs from another category.
- No duplicates within an array.
- Match by meaning, not wording: handle synonyms, descriptive variants, and context-resolved references. Prefer the single most precise canonical asset; never create a new asset when one fits, and never pick two when one clearly represents the entity.
- Use reasonable contextual interpretation (`"She picks it up."` → ground `she` and `it` from the synopsis), but do not over-infer from genre conventions, location, character associations, or prior scenes.
- Context informs selection; it never overrides the current subscene's visual requirements.

## SELECTION TEST
For each asset ask: *"If removed, would the subscene become materially incorrect, incomplete, or misleading?"* Yes → select. No → omit. Applies to characters and props; world is the exception since every subscene needs exactly one. Continuity only settles borderline cases.

## EXAMPLES
```json
{"scene_id": "S1A", "char_ids": ["C1"], "props": ["P1"], "world": "W1"}
```
`"Maya holds the lantern above her head."` → `C1` (Maya), `P1` (Lantern), `W1` (forest).

```json
{"scene_id": "S1B", "char_ids": [], "props": [], "world": "W1"}
```
`"The forest is silent beneath the moon."` → environment-only; do not force a character in.

```json
{"scene_id": "S1C", "char_ids": ["C1", "C2"], "props": [], "world": "W2"}
```
`"Maya speaks to her grandmother."` → both visually required.

```json
{"scene_id": "S1D", "char_ids": ["C1", "C2", "C3"], "props": ["P1"], "world": "W1"}
```
`"Maya, her grandmother, and Tomas watch the lantern drift downstream."` with `prev_subscene = S1C` → `S1C` grounded `C1`+`C2`, but `S1D` explicitly adds Tomas (`C3`).

```json
{"scene_id": "S1E", "char_ids": ["C1", "C2"], "props": [], "world": "W1"}
```
Same situation as `S1D` but `S1D` was `{"char_ids": ["C1", "C2", "C3"], "props": ["P1"]}` and this description names only Maya and her grandmother → continuity keeps `C1`+`C2`, but `C3` and the lantern are not visibly required now, so both drop. Continuity prevents drift, it does not freeze the cast.

`"Maya walks through the forest."` → `"props": []` (no arbitrary props).

`"Maya enters the old wooden cabin."` with `W2 = Old Wooden Cabin` → `"world": "W2"`.

`"She carries a small oil lamp."` with `P1 = Lantern` → `"props": ["P1"]`.

`"Tomas steps out."` with `prev_ingredients` containing `C3` → `C3` dropped; that is an explicit contradiction.

`S2A` with `prev_subscene = None` → no carry-over from `S1D`, regardless of what happened before it.

## FINAL CHECK (internal)
1. Exactly one object, `scene_id` copied from `current_subscene`, valid JSON, no text outside it.
2. Every selected character is visually present/participating and in the registry; absent/mentioned-only excluded; `[]` used when none; no duplicates.
3. Every selected prop is visually required and in the registry; incidental objects excluded; `[]` used when none; no duplicates.
4. Exactly one world, registry-valid, primary environment, not empty/null/array.
5. Continuity honored: characters and props present in `prev_ingredients` kept unless the current description contradicts; nothing carried in when `prev` is `None`; nothing invented to justify an inherited asset.

## INPUT DATA
```text
{{STORY_SYNOPSIS}}
```
```json
{{CURRENT_SUBSCENE}}
```
```json
{{PREV_SUBSCENE}}
```
```json
{{PREV_INGREDIENTS}}
```
```json
{{CHARACTERS}}
```
```json
{{PROPS}}
```
```json
{{WORLDS}}
```

Read the synopsis first for global context, then the previous subscene and its ingredients, then judge the current subscene: one world, zero-or-more characters, zero-or-more props — the minimum sufficient set. Return only the JSON object.