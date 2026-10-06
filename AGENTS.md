# AGENTS.md

Flat, single-module Python pipeline: no package, no tests, no lint/CI config, no
`__init__.py`. Everything lives in `src/` and imports are top-level siblings.

## Running it

- **CWD must be `src/`.** `cli.py:57` / `main.py:31` use `Path("prompts")`, all
  imports are flat, and `.env.config` workflow paths are `./comfyui_workflow/*.json`.
  The README's `python src/main.py` from the repo root fails the prompts check.
- Interpreter is a **Windows venv**: `.venv/Scripts/python.exe` (Python 3.12). No
  `.venv/bin`, even from a WSL/Linux shell. `git` is also absent from that shell.

  ```bash
  cd src
  ../.venv/Scripts/python.exe main.py \
      --story-dir stories/test \
      --input-dir stories/test \
      --image-backend openrouter
  ```

  `stories/test` (gitignored) is the only local story dir; the README's
  `stories/metamorphosis` does not exist.
- `--image-backend` is `required=True` (`cli.py:40`), so even `--skip-image` runs must
  pass it. It is validated before `--help` output is used — import-time env checks in
  `config.py` raise `ValueError` on the first missing var, including `COMFY_URL` and the
  three `*_WORKFLOW_FILE` vars that are irrelevant for `openrouter`.
- Env load order is `.env.secrets` then `.env.config` with `override=False`, so secrets
  win and an empty `.env.config` value does **not** clear a secret.
  `OPENROUTER_API_KEY` falls back to `LLM_API_KEY`.
- **Storyboards are a separate entrypoint**, not part of `main.py`:
  `cd src && ../.venv/Scripts/python.exe storyboard.py stories/test`. It needs
  `generated_metadata/scenes_metadata.json` + `generated_output/final_images`; its
  default story dir (`stories/metamorphosis`) does not exist locally.
- Passing `--story-dir` equal to `--input-dir` works only because `preprocess_input`
  skips its own `combined_input.md` output while globbing (`helper_fn.py:43`).

## Verification

No test/lint/typecheck command exists (`ruff` is not in `requirements.txt` or the venv,
despite stray `.ruff_cache/` dirs). The only meaningful check is a metadata-only run:
`--skip-image --skip-valid` on `stories/test`, then read
`stories/test/generated_metadata/*.json` — those files are both the output and the
resume cache, so they are the artifact to inspect.

## Pipeline architecture

- `main.py` = 5 LLM metadata stages then 3 image passes; stage functions live in
  `components.py` (`generate_meta_stage1..5`; `generate_item` = one uncached LLM call
  with no checkpoint). Stage 1 fans out 4 concurrent calls via `asyncio.gather`, which
  is what drives the rate-limit handling in `llm_api.py`.
- `pydantic_models.py` is the contract for every stage (outlines constrains generation
  to the schema), so schema and prompt changes must ship together.
- Prompts are `src/prompts/{t2t,t2i}/*.md` with `{{PLACEHOLDER}}` tokens substituted by
  plain `str.replace` (`components.py:116`). Placeholder names must match the dict keys
  passed from `main.py`; a mismatch silently ships literal `{{...}}` into the prompt.
- Model-authored IDs follow conventions other code depends on: subscene `S1A` → parent
  `S1` via `parent_scene_id()`, used for stage-3 continuity and by
  `storyboard.group_subscene_images` (longest-prefix match so `S25A` isn't claimed by
  `S2`). Changing the ID shape breaks continuity silently.
- Retry architecture (`llm_api.py`): transport faults are retried 3x with backoff +
  jitter inside `call_with_retry` and never consume the schema budget in `run_model`;
  a schema miss first triggers one `repair_output` heal call (plus a single-field plain
  text `[COERCE]` fallback) before a regeneration attempt. `run_model` returns `None`
  only after exhausting `max_retries`; callers turn that into `RuntimeError` after
  saving partial progress. Every call sends `extra_body={"reasoning": {"effort": ...}}`,
  so the endpoint must tolerate that field.
- Checkpoint/resume: each stage writes `<story_dir>/generated_metadata/<stage>.json`,
  reorders/prunes entries to upstream order on flush, and regenerates only missing IDs.
  Stage 1 calls pass `dependent_paths`; when the upstream file is absent its downstream
  files are **deleted** (`components.py:88`) — don't hand-delete a metadata file without
  checking what that invalidates. Stage 2's on-disk shape is `SubSceneCheckpoint`
  (`subscenes` + `scenes_done`) and old `<stage>.progress.json` sidecars are imported
  once then deleted (`helper_fn.import_legacy_progress`). Stage 3 relabels a returned
  `scene_id` that doesn't match the requested subscene with `[WARN]`.
  `--replace` forces a clean rebuild; without it, re-running retries only failed items.
- Images are named by ID and existing files are skipped: `char_images/<char_id>.png`
  (`3:4`), `world_images/<world_id>.png` (`16:9`), `final_images/<subscene_id>.png`.
  Final scenes composite `temp_images/char_merge{1,2}.png` (character sheet split ~half
  each) with the world plate; a missing world plate is reported in `[FINAL-MISSING]`
  and skipped, not raised. `unload_backend` runs only at the end of the final pass and
  is a no-op for `openrouter`.
- ComfyUI workflow JSONs are **prompt format**, and node IDs are hardcoded in
  `image_api.py` (t2i: `459_452` prompt, `459_458` sampler, `459_456` resolution, `462`
  image id; i2i: `477`/`480`/`470` reference images, `459_474` prompt, `459_458`,
  `459_456`, `479`). A custom workflow must keep those IDs or `image_api.py` needs
  editing too.
- The `openrouter` backend ignores `width`/`height`/`cfg`/`steps` from `main.py` and
  sends only `aspect_ratio` + `resolution`; only the `comfyui` path honors those params.

## Conventions

- Flat sibling imports (`import pydantic_models as pyd`, `from components import ...`) —
  keep it that way unless you also fix the CWD coupling.
- Match surrounding style: 4-space indent, ~79-col black-ish formatting, double quotes,
  `[TAG]` progress prints (`[STEP]`, `[SAVE]`, `[SKIP]`, `[RESUME]`, `[FAILED]`,
  `[RATE-LIMIT]`, `[IMAGE-*]`, `[FINAL-*]`, `[BOARD-*]`).
- Output directories are created by `main.py`; don't assume they exist when calling a
  stage function directly.
- `.gitignore` excludes `AGENTS.md`, `.env.config`, `.env.secrets`, `src/stories/`,
  `stories`, and `.venv`, so local artifacts and this file never get committed.
