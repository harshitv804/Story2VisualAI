# SCENES → WORLD/BACKGROUND METADATA

## ROLE
Analyze the complete ordered scene list **in one pass** and return the deduplicated set of detailed world/location/background environments for the whole story. Output only world metadata — no props, characters, title, synopsis, style, camera directions, prompts, or dialogue.

## INPUT
- `scenes`: the complete ordered list of scene metadata (`scene_id`, `scene_desc`).

## OUTPUT
Valid JSON only — no markdown, no explanation:

```json
{
  "worlds": [
    {"world_id": "W1", "name": "", "world_desc": ""}
  ]
}
```

Return **every distinct location** that visibly appears. Typically **5–8 worlds for 20–30 scenes**. Returning a single world for a many-location story is a **failure** — re-analyze.

## PROCEDURE
1. Read all scenes in order; count distinct locations (do not collapse to one).
2. `S1`: identify the visible primary world(s); create `W1…` with `world_desc` grounded in `S1`.
3. `S2…Sn`: check each against existing worlds. Same canonical location → **reuse the entry**, enriching `world_desc` with any new visual detail. New location → create a new world ID. Never ignore a location not yet seen.
4. Merge references to the same canonical place ("old cottage" / "family cottage" / "the cottage by the river" → one world).
5. Assign final sequential IDs `W1, W2, W3…` in order of first appearance.
6. Write concise, information-dense `world_desc` for each.
7. Final validation: confirm all distinct worlds are present.

## WORLD DEFINITION
A reusable physical environment serving as visual background (village street, bedroom, kitchen, police station, harbor, forest, beach, classroom). Include worlds that are visible/central to at least one scene, visually distinctive, important for spatial consistency, and detailed enough for image generation.

- Include scene-level visual detail — architecture, materials, lighting — as seen in the scenes where the world appears; enrich across all appearances.
- Weather/time-of-day only if visually present in that world's scenes (e.g. "rain-washed window ledge", "sunlit pool deck").

## IDS & NAMES
- IDs: final stable sequential `W1, W2, W3…`, ordered by first appearance.
- `name`: concise canonical location name in Title case (e.g. `"Gregor's Room"`, `"Samsa Apartment Living Room"`, `"Village Main Street"`).

## `world_desc`
One dense string of compact comma-separated fragments giving the location's scene-detailed visual identity, enriched across all its appearances. Preferred structure:

```text
location type, spatial layout across scenes, major structures, architecture details, materials, lighting/atmosphere as described, dominant colors, distinctive features, historical/style impression
```

Example:
```json
{
  "world_id": "W1",
  "name": "Gregor's Room",
  "world_desc": "Small proper human bedroom as seen across morning rain scenes, plain bed with blanket, old heavy chest of drawers, writing desk fixed to floor, leather sofa against wall, table with unpacked cloth samples, gilt-framed magazine picture on wall, tall window with metal ledge and rain droplets, flowered wallpaper, carpet floor, sober inherited furniture, dim gray rain-washed daylight, soft shadows, cramped neglected atmosphere"
}
```

Style: `"Quiet rural train station, low brick building, narrow platform, simple wooden shelter, aged iron benches, gravel track bed, sparse grass, muted weathered materials, early-20th-century provincial architecture, light rain on platform"` — **not** literary prose like `"The train station is a quiet place where characters meet..."`.

## DEDUP (CRITICAL)
One-shot mode must deduplicate: never create a new world for a duplicate location.
- "old cottage" / "family cottage" / "the cottage" → one world.
- "Village street" / "Village street at night" → one world (weather is scene state, not a new world).
- Same world in multiple scenes → **one entry only**, with `world_desc` enriched from all appearances.

## FINAL CHECK (internal)
1. Every distinct visible location has exactly one entry; no duplicates.
2. IDs sequential `W1…` by first appearance; names Title case.
3. Each `world_desc` is one dense, scene-grounded string.
4. Valid JSON, double quotes, no markdown, no extra fields.

## SCENES INPUT
```json
{{SCENES}}
```

Go through the scenes in order, deduplicate, and return only the final `worlds` JSON.
