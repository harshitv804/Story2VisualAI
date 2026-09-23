import gc
import json
from pathlib import Path

import pydantic_models as pyd
from helper_fn import has_json_data, read_md
from image_api import (
    create_image_layout,
    generate_image_to_image,
    generate_text_to_image,
    unload_models,
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
        print(f"[SKIP] Story validation already exists -> '{story_valid_path}'")

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
    dependent_paths: list[Path] | None = None
):
    print()
    print(f"[STEP] Generate {name}:")

    result = None

    if check_existing and not output_path.exists() and dependent_paths:
        for dependent_path in dependent_paths:
            if dependent_path.exists():
                dependent_path.unlink()
                print(f"[DELETE] Dependent file -> '{dependent_path}'")

    # Reuse existing output only when requested
    if check_existing and output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                print(f"[SKIP] {name} already exists -> '{output_path}'")
                result = output_schema.model_validate(existing)
            else:
                print(f"[INFO] {name} is empty, regenerating -> '{output_path}'")

        except Exception as e:
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

    result = None

    # Reuse existing output only if JSON actually contains data
    if output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                print(f"[SKIP] {name} already exists -> '{output_path}'")
                result = output_schema.model_validate(existing)
            else:
                print(f"[INFO] {name} is empty, regenerating -> '{output_path}'")

        except Exception as e:
            print(f"[WARN] Failed to load existing {name}: {e}")

    if result is None:
        result = pyd.SubSceneMetadata()
        for i, scene in enumerate(input_json.scenes):
            print()
            print(
                f"[STEP] Generate subscenes {i + 1}/{len(input_json.scenes)}: {scene.scene_id}"
            )

            # Previous scene
            prev_scene = input_json.scenes[i - 1] if i > 0 else None

            prev_scene_json = (
                prev_scene.model_dump_json(indent=2)
                if prev_scene is not None
                else "None"
            )

            # Current scene
            current_scene_json = scene.model_dump_json(indent=2)

            # Generate metadata for this scene
            scene_result = await generate_meta_stage1(
                name,
                {
                    "PREV_SCENE": prev_scene_json,
                    "CURRENT_SCENE": current_scene_json,
                },
                output_path,
                output_schema,
                prompts_path,
                check_existing=False,
                save_output=False,
            )

            result.subscenes.extend(scene_result.subscenes or [])

        output_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"[SAVE] Subscenes metadata -> '{output_path}'")
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

    result = None

    # Reuse existing output only if JSON actually contains data
    if output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                print(f"[SKIP] {name} already exists -> '{output_path}'")

                result = pyd.SceneIngredientsList.model_validate(existing)
            else:
                print(f"[INFO] {name} is empty, regenerating -> '{output_path}'")

        except Exception as e:
            print(f"[WARN] Failed to load existing {name}: {e}")

    if result is None:
        result = pyd.SceneIngredientsList(ingredients=[])

        for i, subscene in enumerate(subscene_meta.subscenes):
            print()
            print(
                f"[STEP] Generate scene ingredients "
                f"({i + 1}/{len(subscene_meta.subscenes)}): "
                f"{subscene.scene_id}"
            )

            # Current subscene only
            subscene_json = json.dumps(
                {
                    "subscene_id": subscene.scene_id,
                    "subscene_desc": subscene.scene_desc,
                },
                indent=2,
            )

            # Shared context + current subscene
            inputs = {
                **context_inputs,
                "SUBSCENES": subscene_json,
            }

            scene_result = await generate_meta_stage1(
                name,
                inputs,
                output_path,
                output_schema,
                prompts_path,
                check_existing=False,
                save_output=False,
            )

            # Accumulate generated ingredients
            result.ingredients.extend(scene_result.ingredients or [])

        # Incremental save
        output_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

        print(f"[SAVE] Scene ingredients -> '{output_path}'")

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

    result = None

    if output_path.exists() and not replace:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                print(f"[SKIP] {name} already exists -> '{output_path}'")

                result = list_schema.model_validate(existing)

            else:
                print(f"[INFO] {name} is empty, regenerating -> '{output_path}'")

        except Exception as e:
            print(f"[WARN] Failed to load existing {name}: {e}")

    if result is None:
        result = list_schema(prompts=[])

        for i, item in enumerate(items):
            item_id = getattr(
                item,
                id_field,
            )

            print()
            print(f"[STEP] Generate image prompt ({i + 1}/{len(items)}): {item_id}")

            item_json = item.model_dump_json(indent=2)

            inputs = {
                **context_inputs,
                meta_variable: item_json,
            }

            generated = await generate_meta_stage1(
                name,
                inputs,
                output_path,
                output_schema,
                prompts_path,
                check_existing=False,
                save_output=False,
            )

            final_prompt = item_schema(
                **{
                    id_field: item_id,
                    "image_prompt": generated.image_prompt,
                }
            )

            result.prompts.append(final_prompt)

        output_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

        print(f"[SAVE] Image prompt -> '{output_path}'")

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

    if final_img_meta_path.exists() and not replace:
        try:
            existing = json.loads(final_img_meta_path.read_text(encoding="utf-8"))

            if has_json_data(existing):
                print(
                    f"[SKIP] Final image prompts already exist "
                    f"-> '{final_img_meta_path}'"
                )

                return pyd.FinalImagePromptList.model_validate(existing)

            else:
                print(
                    f"[INFO] Final image prompts are empty, "
                    f"regenerating -> '{final_img_meta_path}'"
                )

        except Exception as e:
            print(f"[WARN] Failed to load existing final image prompts: {e}")

    subscenes = {
        subscene.scene_id: subscene for subscene in (subscene_meta.subscenes or [])
    }

    characters = {char.char_id: char for char in (character_meta.characters or [])}

    props = {prop.prop_id: prop for prop in (prop_meta.props or [])}

    worlds = {world.world_id: world for world in (world_meta.worlds or [])}

    result = pyd.FinalImagePromptList()

    ingredients = scene_requirements.ingredients

    for i, ingredient in enumerate(ingredients):
        item_id = ingredient.scene_id

        print(
            f"[STEP] Generate final image prompt "
            f"({i + 1}/{len(ingredients)}): {item_id}"
        )

        scene = subscenes[item_id]

        chars = [characters[char_id] for char_id in ingredient.char_ids]

        props_list = [props[prop_id] for prop_id in ingredient.props]

        world = worlds[ingredient.world]

        output_prompt = await generate_meta_stage1(
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
            check_existing=False,
            save_output=False,
        )

        result.results.append(
            pyd.FinalImagePrompt(
                subscene_id=item_id,
                char_ids=ingredient.char_ids,
                world_id=ingredient.world,
                image_prompt=output_prompt,
            )
        )

    final_img_meta_path.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(f"[SAVE] Final image prompt -> '{final_img_meta_path}'")

    return result


def generate_meta_images(
    prompts,
    output_dir,
    image_params: list,
    id_field: str,
):

    image_width, image_height, image_guidance, image_steps = image_params

    for item in prompts.prompts:
        item_id = getattr(item, id_field)
        prompt_text = item.image_prompt

        out_path = output_dir / f"{item_id}.png"

        if out_path.exists():
            print()
            print(f"[IMAGE-SKIP] {item_id} already exists -> {out_path}")
            continue

        try:
            print()
            print(f"[IMAGE-GEN] {item_id}")

            generate_text_to_image(
                prompt=prompt_text,
                output_path=out_path,
                image_id=item_id,
                width=image_width,
                height=image_height,
                cfg=image_guidance,
                steps=image_steps,
            )
            print()
            print(f"[IMAGE-SAVED] {item_id} -> '{out_path}'")

        except Exception as e:
            print()
            print(f"[IMAGE-ERROR] {item_id} failed: {e}")

        finally:
            gc.collect()


def generate_final_scene_images(
    final_image_prompts,
    character_meta,
    image_params,
    generated_final_images_dir,
    generated_char_images_dir,
    generated_world_images_dir,
    generated_temp_images_dir,
):

    image_width, image_height, image_guidance, image_steps = image_params

    # char_id -> Character
    characters = {char.char_id: char for char in (character_meta.characters or [])}

    for item in final_image_prompts.results:
        subscene_id = item.subscene_id
        char_ids = item.char_ids or []
        world_id = item.world_id
        prompt_text = item.image_prompt.image_prompt

        final_image_path = generated_final_images_dir / f"{subscene_id}.png"

        if final_image_path.exists():
            print()
            print(f"[FINAL] Skipping {subscene_id} (already exists)")
            continue

        try:
            char_data_for_layout = []

            for cid in char_ids:
                char = characters.get(cid)

                if char is None:
                    print()
                    print(f"[FINAL-WARN] Character {cid} not found for {subscene_id}")
                    continue

                img_path = generated_char_images_dir / f"{cid}.png"

                if not img_path.exists():
                    print()
                    print(f"[FINAL-WARN] Character image missing: {img_path}")
                    continue

                char_data_for_layout.append(
                    {
                        "image": img_path,
                        "name": char.name,
                        "id": char.char_id,
                    }
                )

            layout_path = create_image_layout(
                char_data_for_layout,
                generated_temp_images_dir,
            )
            print()
            print(f"[FINAL] Layout created for {subscene_id}: {layout_path}")

            world_image_path = generated_world_images_dir / f"{world_id}.png"

            if not world_image_path.exists():
                print()
                print(f"[FINAL-WARN] World image missing: {world_image_path}")
                continue

            print(f"[FINAL] World image: {world_image_path}")

            generate_image_to_image(
                prompt=prompt_text,
                image_1=layout_path,
                image_2=world_image_path,
                output_path=final_image_path,
                image_id=subscene_id,
                width=image_width,
                height=image_height,
                cfg=image_guidance,
                steps=image_steps,
            )
            print(f"[FINAL-SAVED] {subscene_id} -> '{final_image_path}'")
            print()

        except Exception as e:
            print()
            print(f"[FINAL-ERROR] {subscene_id} failed: {e}")

        finally:
            gc.collect()

    unload_models()
