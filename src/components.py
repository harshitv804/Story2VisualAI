import gc
import json
import re
from pathlib import Path

import pydantic_models as pyd
from helper_fn import (
    has_json_data,
    import_legacy_progress,
    read_md,
)
from image_api import (
    IMAGE_BACKENDS,
    LANDSCAPE_ASPECT_RATIO,
    create_image_layout,
    image_to_image,
    text_to_image,
    unload_backend,
)
from llm_api import run_model


async def story_validation(
    story_text: str,
    story_valid_path: Path,
    output_schema,
    combined_input_file_path: Path,
    prompts_path: Path,
    replace: bool = False,
):
    print()
    print(f"[GATE] Validating story -> '{combined_input_file_path}'")

    if (
        story_valid_path.exists()
        and not replace
        and story_valid_path.read_text(encoding="utf-8").strip()
    ):
        print("[SKIP] Story validation already exists")

        try:
            existing = json.loads(story_valid_path.read_text(encoding="utf-8"))
            result = output_schema.model_validate(existing)

        except Exception as e:
            print(f"[WARN] Failed to load existing validation: {e}")
            result = None

    else:
        prompt_template = read_md(prompts_path)
        prompt = prompt_template.replace("{{STORY}}", story_text)

        result = await run_model(
            "story_validation", prompt, output_schema, reasoning="medium"
        )

        story_valid_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    if result is None:
        raise RuntimeError("[ERROR] Story validation failed after retries.")

    if not result.valid:
        raise RuntimeError("[ERROR] Story is invalid.")

    print("[VALID] Story is valid!")


async def generate_meta_stage1(
    name: str,
    inputs: dict[str, str],
    output_path: Path,
    output_schema,
    prompts_path: Path,
    replace: bool = False,
    check_existing: bool = True,
    save_output: bool = True,
    dependent_paths: list[Path] | None = None,
    log: bool = True,
):
    if log:
        print()
        print(f"[STEP] Generate {name}:")

    result = None

    if check_existing and not output_path.exists() and dependent_paths:
        for dependent_path in dependent_paths:
            if dependent_path.exists():
                dependent_path.unlink()
                if log:
                    print(f"[DELETE] Dependent file -> '{dependent_path}'")

    # Reuse existing output only when requested
    if check_existing and output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                if log:
                    print(f"[SKIP] {name} already exists")
                result = output_schema.model_validate(existing)
            elif log:
                print(f"[INFO] {name} is empty, regenerating -> '{output_path}'")

        except Exception as e:
            if log:
                print(f"[WARN] Failed to load existing {name}: {e}")

    if result is None:
        prompt_template = read_md(prompts_path)

        prompt = prompt_template
        for key, value in inputs.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", value)

        result = await run_model(
            name,
            prompt,
            output_schema,
        )

        if save_output:
            output_path.write_text(
                result.model_dump_json(indent=2),
                encoding="utf-8",
            )

    if result is None:
        raise RuntimeError(f"[ERROR] {name} failed after retries.")

    return result


async def generate_item(
    name: str,
    inputs: dict[str, str],
    output_path: Path,
    output_schema,
    prompts_path: Path,
):
    """One LLM call for a single item of a stage."""

    return await generate_meta_stage1(
        name,
        inputs,
        output_path,
        output_schema,
        prompts_path,
        check_existing=False,
        save_output=False,
        log=False,
    )


def parent_scene_id(subscene_id: str) -> str:
    """Group id of a subscene: S1A -> S1, S12C -> S12.

    Returns the id unchanged when it carries no trailing letter suffix.
    """

    match = re.match(r"^(.*?)[A-Z]+$", subscene_id)

    return match.group(1) if match else subscene_id


def report_failures(name: str, failed: list[str]):
    if not failed:
        return

    print()
    print(f"[FAILED] {name}: {len(failed)} item(s) -> {', '.join(failed)}")
    print("[HINT] Re-run the same command to retry only these items")


async def generate_meta_stage2(
    name: str,
    input_json,
    output_path: Path,
    output_schema,
    prompts_path: Path,
    replace: bool = False,
):
    print()
    print(f"[STEP] Generate {name}:")

    scenes = input_json.scenes

    total = len(scenes)

    result = pyd.SubSceneMetadata(subscenes=[])

    done = set()

    # Subscenes carry no parent id, so completed scenes are tracked in the
    # stage output itself under 'scenes_done'
    if output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                checkpoint = pyd.SubSceneCheckpoint.model_validate(existing)

                result = pyd.SubSceneMetadata(subscenes=checkpoint.subscenes)
                done = set(checkpoint.scenes_done)
            else:
                print(f"[INFO] {name} is empty, regenerating")

        except Exception as e:
            print(f"[WARN] Failed to load existing {name}: {e}")

    done |= import_legacy_progress(output_path)

    pending = [
        (index, scene)
        for index, scene in enumerate(scenes, start=1)
        if scene.scene_id not in done
    ]

    if done:
        print(f"[RESUME] {len(done)}/{total} already done")

    if not pending:
        print(f"[SKIP] {name} already exists")
        return result

    failed = []

    for index, scene in pending:
        print()
        print(
            f"[STEP] Generate subscenes "
            f"({index}/{total}): {scene.scene_id}"
        )

        # Previous scene
        prev_scene = scenes[index - 2] if index > 1 else None

        prev_scene_json = (
            prev_scene.model_dump_json(indent=2)
            if prev_scene is not None
            else "None"
        )

        # Current scene
        current_scene_json = scene.model_dump_json(indent=2)

        try:
            scene_result = await generate_item(
                name,
                {
                    "PREV_SCENE": prev_scene_json,
                    "CURRENT_SCENE": current_scene_json,
                },
                output_path,
                output_schema,
                prompts_path,
            )
        except Exception as e:
            print(f"[ERROR] {scene.scene_id} failed: {e}")
            failed.append(scene.scene_id)
            continue

        result.subscenes.extend(scene_result.subscenes or [])

        done.add(scene.scene_id)

        output_path.write_text(
            pyd.SubSceneCheckpoint(
                subscenes=result.subscenes,
                scenes_done=sorted(done),
            ).model_dump_json(indent=2),
            encoding="utf-8",
        )

        print(f"[SAVE] subscenes ({index}/{total})")

    print(f"[SAVE] {name} {len(result.subscenes)} subscenes -> '{output_path}'")

    if failed:
        report_failures(name, failed)
        raise RuntimeError(
            f"[ERROR] {name} incomplete: {len(failed)} scene(s) failed. "
            f"Progress saved, re-run to continue."
        )

    return result


async def generate_meta_stage3(
    name: str,
    subscene_meta,
    context_inputs: dict[str, str],
    output_path: Path,
    output_schema,
    prompts_path: Path,
    replace: bool = False,
):
    print()
    print(f"[STEP] Generate {name}:")

    subscenes = subscene_meta.subscenes

    total = len(subscenes)

    result = pyd.SceneIngredientsList(ingredients=[])

    # Reuse existing output only if JSON actually contains data
    if output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                result = pyd.SceneIngredientsList.model_validate(existing)
            else:
                print(f"[INFO] {name} is empty, regenerating")

        except Exception as e:
            print(f"[WARN] Failed to load existing {name}: {e}")

    order = {subscene.scene_id: i for i, subscene in enumerate(subscenes)}

    subscenes_by_id = {subscene.scene_id: subscene for subscene in subscenes}

    # Previous subscene within the same parent scene, for continuity.
    # S1B -> S1C, and the first subscene of a scene has no predecessor.
    prev_subscene_id = {}

    last_in_group = {}

    for subscene in subscenes:
        group = parent_scene_id(subscene.scene_id)

        prev_subscene_id[subscene.scene_id] = last_in_group.get(group)

        last_in_group[group] = subscene.scene_id

    def ingredients_by_id() -> dict:
        return {entry.scene_id: entry for entry in result.ingredients}

    def flush() -> None:
        # One entry per subscene; a duplicated id keeps the latest result
        latest = {entry.scene_id: entry for entry in result.ingredients}

        result.ingredients = [
            latest[scene_id]
            for scene_id in sorted(latest, key=lambda sid: order[sid])
            if scene_id in order
        ]
        output_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    subscene_ids = {subscene.scene_id for subscene in subscenes}

    done = {
        ingredient.scene_id
        for ingredient in result.ingredients
        if ingredient.scene_id in subscene_ids
    }

    pending = [
        (index, subscene)
        for index, subscene in enumerate(subscenes, start=1)
        if subscene.scene_id not in done
    ]

    if done:
        print(f"[RESUME] {len(done)}/{total} already done")

    if not pending:
        flush()
        print(f"[SKIP] {name} already exists")
        return result

    failed = []

    for index, subscene in pending:
        print()
        print(
            f"[STEP] Generate scene ingredients "
            f"({index}/{total}): {subscene.scene_id}"
        )

        # Current subscene only
        current_subscene_json = json.dumps(
            {
                "scene_id": subscene.scene_id,
                "scene_desc": subscene.scene_desc,
            },
            indent=2,
        )

        # Preceding subscene of the same parent scene, plus its ingredients
        prev_id = prev_subscene_id[subscene.scene_id]

        prev_subscene = subscenes_by_id.get(prev_id) if prev_id else None

        prev_ingredient = (
            ingredients_by_id().get(prev_id) if prev_id else None
        )

        # Shared context + current subscene + continuity reference
        inputs = {
            **context_inputs,
            "CURRENT_SUBSCENE": current_subscene_json,
            "PREV_SUBSCENE": (
                prev_subscene.model_dump_json(indent=2)
                if prev_subscene is not None
                else "None"
            ),
            "PREV_INGREDIENTS": (
                prev_ingredient.model_dump_json(indent=2)
                if prev_ingredient is not None
                else "None"
            ),
        }

        try:
            scene_result = await generate_item(
                name,
                inputs,
                output_path,
                output_schema,
                prompts_path,
            )
        except Exception as e:
            print(f"[ERROR] {subscene.scene_id} failed: {e}")
            failed.append(subscene.scene_id)
            continue

        # Accumulate generated ingredients, keyed to the requested subscene
        for entry in scene_result.ingredients or []:
            if entry.scene_id != subscene.scene_id:
                print(
                    f"[WARN] {subscene.scene_id}: got scene_id "
                    f"'{entry.scene_id}', relabelled"
                )
                entry.scene_id = subscene.scene_id

            result.ingredients.append(entry)

        # Incremental save
        flush()

        print(f"[SAVE] ingredients ({index}/{total})")

    print(f"[SAVE] {name} {len(result.ingredients)} items -> '{output_path}'")

    if failed:
        report_failures(name, failed)
        raise RuntimeError(
            f"[ERROR] {name} incomplete: {len(failed)} subscene(s) failed. "
            f"Progress saved, re-run to continue."
        )

    return result


async def generate_meta_stage4(
    name: str,
    items,
    context_inputs: dict[str, str],
    output_path: Path,
    prompts_path: Path,
    id_field: str,
    meta_variable: str,
    output_schema,
    item_schema,
    list_schema,
    replace: bool = False,
):
    print()
    print(f"[STEP] Generate {name}:")

    result = list_schema(prompts=[])

    if output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            result = list_schema.model_validate(existing)

        except Exception as e:
            print(f"[WARN] Failed to load existing {name}: {e}")
            result = list_schema(prompts=[])

    order = {getattr(item, id_field): i for i, item in enumerate(items)}

    def flush() -> None:
        result.prompts = [
            entry for entry in result.prompts if getattr(entry, id_field) in order
        ]
        result.prompts.sort(
            key=lambda entry: order[getattr(entry, id_field)],
        )
        output_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    completed_ids = {getattr(entry, id_field) for entry in result.prompts}

    pending = [
        item for item in items if getattr(item, id_field) not in completed_ids
    ]

    if completed_ids:
        print(f"[RESUME] {len(completed_ids)}/{len(items)} already done")

    if not pending:
        flush()
        print(f"[SKIP] {name} already exists")
        return result

    failed = []

    for i, item in enumerate(pending):
        item_id = getattr(
            item,
            id_field,
        )

        print()
        print(f"[STEP] Generate image prompt ({i + 1}/{len(pending)}): {item_id}")

        item_json = item.model_dump_json(indent=2)

        inputs = {
            **context_inputs,
            meta_variable: item_json,
        }

        try:
            generated = await generate_item(
                name,
                inputs,
                output_path,
                output_schema,
                prompts_path,
            )
        except Exception as e:
            print(f"[ERROR] {item_id} failed: {e}")
            failed.append(item_id)
            continue

        final_prompt = item_schema(
            **{
                id_field: item_id,
                "image_prompt": generated.image_prompt,
            }
        )

        result.prompts.append(final_prompt)

        flush()

    print(f"[SAVE] {name} {len(result.prompts)}/{len(items)} -> '{output_path}'")

    if failed:
        report_failures(name, failed)
        raise RuntimeError(
            f"[ERROR] {name} incomplete: {len(failed)} item(s) failed. "
            f"Progress saved, re-run to continue."
        )

    return result


async def generate_meta_stage5(
    scene_requirements,
    subscene_meta,
    character_meta,
    prop_meta,
    world_meta,
    story_meta,
    final_img_meta_path,
    prompts_dir,
    replace=False,
) -> pyd.FinalImagePromptList:

    print()
    print("[STEP] Generate final image prompts:")

    result = pyd.FinalImagePromptList(results=[])

    if final_img_meta_path.exists() and not replace:
        try:
            existing = json.loads(final_img_meta_path.read_text(encoding="utf-8"))

            result = pyd.FinalImagePromptList.model_validate(existing)

        except Exception as e:
            print(f"[WARN] Failed to load existing final image prompts: {e}")
            result = pyd.FinalImagePromptList(results=[])

    subscenes = {
        subscene.scene_id: subscene for subscene in (subscene_meta.subscenes or [])
    }

    characters = {char.char_id: char for char in (character_meta.characters or [])}

    props = {prop.prop_id: prop for prop in (prop_meta.props or [])}

    worlds = {world.world_id: world for world in (world_meta.worlds or [])}

    ingredients = scene_requirements.ingredients

    # Keep the output ordered like the requirements it was built from
    order = {ingredient.scene_id: i for i, ingredient in enumerate(ingredients)}

    def flush() -> None:
        result.results = [
            entry for entry in result.results if entry.subscene_id in order
        ]
        result.results.sort(
            key=lambda entry: order[entry.subscene_id],
        )
        final_img_meta_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    completed_ids = {item.subscene_id for item in result.results}

    pending = [
        ingredient
        for ingredient in ingredients
        if ingredient.scene_id not in completed_ids
    ]

    if completed_ids:
        print(f"[RESUME] {len(completed_ids)}/{len(ingredients)} already done")

    if not pending:
        flush()
        print("[SKIP] final_image_prompts already exists")
        return result

    failed = []

    for i, ingredient in enumerate(pending):
        item_id = ingredient.scene_id

        print(
            f"[STEP] Generate final image prompt "
            f"({i + 1}/{len(pending)}): {item_id}"
        )

        scene = subscenes[item_id]

        chars = [characters[char_id] for char_id in ingredient.char_ids]

        props_list = [props[prop_id] for prop_id in ingredient.props]

        world = worlds[ingredient.world]

        try:
            output_prompt = await generate_item(
                "final_image_prompt",
                {
                    "SCENE_DESC": json.dumps(
                        scene.model_dump(),
                        indent=2,
                    ),
                    "CHAR_METADATA": json.dumps(
                        [char.model_dump() for char in chars],
                        indent=2,
                    ),
                    "WORLD_METADATA": json.dumps(
                        world.model_dump(),
                        indent=2,
                    ),
                    "PROPS_METADATA": json.dumps(
                        [prop.model_dump() for prop in props_list],
                        indent=2,
                    ),
                    "STORY_STYLE": story_meta.story_style,
                },
                final_img_meta_path,
                pyd.ImagePrompt,
                prompts_dir,
            )
        except Exception as e:
            print(f"[ERROR] {item_id} failed: {e}")
            failed.append(item_id)
            continue

        result.results.append(
            pyd.FinalImagePrompt(
                subscene_id=item_id,
                char_ids=ingredient.char_ids,
                world_id=ingredient.world,
                image_prompt=output_prompt,
            )
        )

        flush()

    print(
        f"[SAVE] final_image_prompts "
        f"{len(result.results)}/{len(ingredients)} -> '{final_img_meta_path}'"
    )

    if failed:
        report_failures("final_image_prompts", failed)
        raise RuntimeError(
            f"[ERROR] final_image_prompts incomplete: "
            f"{len(failed)} subscene(s) failed. "
            f"Progress saved, re-run to continue."
        )

    return result


def generate_meta_images(
    prompts,
    output_dir,
    image_params: list,
    id_field: str,
    backend: str,
    aspect_ratio: str = LANDSCAPE_ASPECT_RATIO,
    resolution: str = "1K",
):
    image_width, image_height, image_guidance, image_steps = image_params

    label = output_dir.name

    generated = []
    skipped = []
    failed = []

    for item in prompts.prompts:
        item_id = getattr(item, id_field)
        prompt_text = item.image_prompt

        out_path = output_dir / f"{item_id}.png"

        if out_path.exists():
            print(f"[IMAGE-SKIP] {item_id} already exists")
            skipped.append(item_id)
            continue

        try:
            text_to_image(
                backend,
                prompt=prompt_text,
                output_path=out_path,
                image_id=item_id,
                width=image_width,
                height=image_height,
                cfg=image_guidance,
                steps=image_steps,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )
            print(f"[IMAGE-SAVED] {item_id} -> '{out_path}'")
            generated.append(item_id)

        except Exception as e:
            print(f"[IMAGE-ERROR] {item_id} failed: {e}")
            failed.append(item_id)

        finally:
            gc.collect()

    total = len(prompts.prompts)

    print(
        f"[IMAGE-DONE] {label}: {len(generated)} generated, {len(skipped)} skipped"
    )

    if failed:
        print(f"[IMAGE-MISSING] {len(failed)}: {', '.join(failed)}")


def generate_final_scene_images(
    final_image_prompts,
    character_meta,
    image_params,
    generated_final_images_dir,
    generated_char_images_dir,
    generated_world_images_dir,
    generated_temp_images_dir,
    backend: str,
    aspect_ratio: str = LANDSCAPE_ASPECT_RATIO,
    resolution: str = "1K",
):
    image_width, image_height, image_guidance, image_steps = image_params

    # char_id -> Character
    characters = {char.char_id: char for char in (character_meta.characters or [])}

    generated = []
    failed = []

    for item in final_image_prompts.results:
        subscene_id = item.subscene_id
        char_ids = item.char_ids or []
        world_id = item.world_id
        prompt_text = item.image_prompt.image_prompt

        final_image_path = generated_final_images_dir / f"{subscene_id}.png"

        if final_image_path.exists():
            print(f"[FINAL-SKIP] {subscene_id} (already exists)")
            continue

        try:
            # BUILD CHARACTER DATA
            char_data_for_layout = []

            for cid in char_ids:
                char = characters.get(cid)

                if char is None:
                    print(f"[FINAL-WARN] Character {cid} not found for {subscene_id}")
                    continue

                img_path = generated_char_images_dir / f"{cid}.png"

                if not img_path.exists():
                    print(f"[FINAL-WARN] Character image missing: {img_path}")
                    continue

                char_data_for_layout.append(
                    {
                        "image": img_path,
                        "name": char.name,
                        "id": char.char_id,
                    }
                )

            char_layout_1, char_layout_2 = create_image_layout(
                char_data_for_layout,
                generated_temp_images_dir,
            )

            print(f"[FINAL] {subscene_id}: layouts ready")

            # WORLD IMAGE
            world_image_path = generated_world_images_dir / f"{world_id}.png"

            if not world_image_path.exists():
                print(f"[FINAL-WARN] World image missing: {world_image_path}")
                failed.append(subscene_id)
                continue

            # GENERATE FINAL IMAGE
            image_to_image(
                backend,
                prompt=prompt_text,
                char_layout_1=char_layout_1,
                char_layout_2=char_layout_2,
                world_image=world_image_path,
                output_path=final_image_path,
                image_id=subscene_id,
                width=image_width,
                height=image_height,
                cfg=image_guidance,
                steps=image_steps,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )

            generated.append(subscene_id)

            print(f"[FINAL-SAVED] {subscene_id} -> '{final_image_path}'")

        except Exception as e:
            print(f"[FINAL-ERROR] {subscene_id} failed: {e}")
            failed.append(subscene_id)

        finally:
            gc.collect()

    total = len(final_image_prompts.results)

    print()
    print(
        f"[FINAL-DONE] {len(generated)} generated, "
        f"{total - len(generated) - len(failed)} skipped"
    )

    if failed:
        print(f"[FINAL-MISSING] {len(failed)}: {', '.join(failed)}")

    unload_backend(backend)
