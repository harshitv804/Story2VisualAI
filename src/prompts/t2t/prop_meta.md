# Prop Metadata Extraction

**Input:** A complete story in plain text.  
**Output:** Prop metadata only, as valid JSON.

## Task

Read the entire story, then extract unique, visually meaningful props that could benefit from consistent reference images.

## Rules

- Include plot-relevant, recurring, distinctive, or handled props. Omit incidental generic objects.
- Merge references to the same prop; keep distinct objects separate.
- Order by narrative importance and assign sequential IDs: `P1`, `P2`, `P3`, …
- Use a concise Title Case name and a dense `prop_desc` of visual details.
- Preserve explicit details. Infer only reasonable missing appearance details from context; do not invent props or unsupported distinctive features.
- Do not include characters, locations, scenes, or any other metadata.
- If there are no meaningful props, return an empty `props` array.

## Output Format

Return only valid JSON with exactly this structure:

```json
{
  "props": [
    {
      "prop_id": "P1",
      "name": "Silver Pocket Watch",
      "prop_desc": "Small antique mechanical pocket watch, round polished silver case, tarnished edges, engraved lid, cream dial, black Roman numerals, thin hands, brass winding crown"
    }
  ]
}
```

## Story

{{STORY}}

---

## Detailed DSPy-Style Prompt

# Story-to-Prop Metadata

**Input:** The complete story as plain text.  
**Output:** A JSON object containing only reusable prop metadata.

## Task

Analyze the entire story before extracting props. Identify each unique object that is important enough to serve as a consistent visual reference across scenes.

## Extraction Guidelines

Include props that are plot-critical, recurring, visually distinctive, used or handled, or important to a scene’s visual identity. Examples include weapons, letters, photographs, keys, vehicles, machines, and distinctive furniture.

Normally omit incidental generic objects such as chairs, plates, walls, floors, and doors unless they are distinctive, recurring, or plot-relevant.

Create one entry for each unique prop identity. Merge repeated references to the same object, but do not merge separate objects merely because they are the same type.

## IDs and Ordering

Order entries by narrative importance:

1. Major plot-critical props
2. Major recurring props
3. Distinctive, visually important props
4. Supporting meaningful props

Assign IDs sequentially in that order: `P1`, `P2`, `P3`, and so on. Do not skip or reuse IDs.

## Field Requirements

- `prop_id`: Sequential ID such as `"P1"`.
- `name`: Concise canonical name in Title Case. Avoid scene-specific wording.
- `prop_desc`: One compact string describing the prop’s canonical visual identity. Use visual fragments separated by commas; do not write a history or narrative sentence.

When supported by the story, describe the object type, approximate size and shape, materials, colors, texture, construction, distinctive features or markings, condition, and era or style. Preserve every explicit attribute.

If the story gives little visual detail about a meaningful prop, fill gaps conservatively using its function and story context. Do not contradict stated details or invent unsupported logos, inscriptions, damage, or other distinctive features.

## Output Requirements

Return valid JSON only—no Markdown, explanation, or extra fields. Use double quotes. Include exactly one top-level `props` array, with every entry containing exactly `prop_id`, `name`, and `prop_desc`. If no meaningful props appear, return `"props": []`.

```json
{
  "props": [
    {
      "prop_id": "P1",
      "name": "Silver Pocket Watch",
      "prop_desc": "Small antique mechanical pocket watch, round polished silver case, tarnished edges, engraved lid, cream enamel dial, black Roman numerals, thin hands, brass winding crown, faint scratches, aged craftsmanship"
    }
  ]
}
```

## Story

{{STORY}}
