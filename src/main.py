import asyncio
import gc
import json
from pathlib import Path

import pydantic_models as pyd
from cli import parse_args
from components import (
    generate_final_scene_images,
    generate_meta_images,
    generate_meta_stage1,
    generate_meta_stage2,
    generate_meta_stage3,
    generate_meta_stage4,
    generate_meta_stage5,
    story_validation,
)
from helper_fn import load_processed_input, preprocess_input


async def main():

    args = parse_args()

    story_dir = Path(args.story_dir).expanduser()
    input_dir = Path(args.input_dir).expanduser()

    combined_input_dir = story_dir / "combined_input"
    generated_metadata_dir = story_dir / "generated_metadata"
    generated_output_dir = story_dir / "generated_output"
    prompts_dir = Path("prompts")

    generated_char_images_dir = generated_output_dir / "char_images"
    generated_world_images_dir = generated_output_dir / "world_images"
    generated_final_images_dir = generated_output_dir / "final_images"
    generated_temp_images_dir = generated_output_dir / "temp_images"

    combined_input_dir.mkdir(parents=True, exist_ok=True)
    generated_metadata_dir.mkdir(parents=True, exist_ok=True)
    generated_output_dir.mkdir(parents=True, exist_ok=True)
    generated_char_images_dir.mkdir(parents=True, exist_ok=True)
    generated_world_images_dir.mkdir(parents=True, exist_ok=True)
    generated_final_images_dir.mkdir(parents=True, exist_ok=True)
    generated_temp_images_dir.mkdir(parents=True, exist_ok=True)

    combined_input_file_path = combined_input_dir / "combined_input.md"

    story_valid_path = generated_metadata_dir / "story_valid_metadata.json"
    story_meta_path = generated_metadata_dir / "story_metadata.json"
    char_meta_path = generated_metadata_dir / "character_metadata.json"
    char_img_meta_path = generated_metadata_dir / "character_image_prompts.json"
    final_img_meta_path = generated_metadata_dir / "final_image_prompts.json"
    world_img_meta_path = generated_metadata_dir / "world_image_prompts.json"
    prop_meta_path = generated_metadata_dir / "prop_metadata.json"
    world_meta_path = generated_metadata_dir / "world_metadata.json"
    scene_meta_path = generated_metadata_dir / "scenes_metadata.json"
    subscene_meta_path = generated_metadata_dir / "subscenes_metadata.json"
    scene_requirements_path = generated_metadata_dir / "scene_requirements.json"

    _ = preprocess_input(input_dir, combined_input_file_path, args.replace)

    story_text = load_processed_input(combined_input_file_path)

    if not args.skip_valid:
        await story_validation(
            story_text,
            story_valid_path,
            pyd.StoryValidation,
            combined_input_file_path,
            prompts_dir / "t2t/story_validation.md",
        )

    story_meta, character_meta, prop_meta, scene_meta = await asyncio.gather(
        generate_meta_stage1(
            "story_metadata",
            {"STORY": story_text},
            story_meta_path,
            pyd.StoryMetadata,
            prompts_dir / "t2t/story_meta.md",
            replace=args.replace,
        ),
        generate_meta_stage1(
            "character_metadata",
            {"STORY": story_text},
            char_meta_path,
            pyd.CharacterMetadata,
            prompts_dir / "t2t/character_meta.md",
            dependent_paths=[char_img_meta_path],
            replace=args.replace,
        ),
        generate_meta_stage1(
            "prop_metadata",
            {"STORY": story_text},
            prop_meta_path,
            pyd.PropMetadata,
            prompts_dir / "t2t/prop_meta.md",
            replace=args.replace,
        ),
        generate_meta_stage1(
            "scene_metadata",
            {"STORY": story_text},
            scene_meta_path,
            pyd.SceneMetadata,
            prompts_dir / "t2t/scene_meta.md",
            dependent_paths=[subscene_meta_path, world_meta_path, final_img_meta_path],
            replace=args.replace,
        ),
    )

    scene_meta_json = [
        {
            "scene_id": scene.scene_id,
            "scene_desc": scene.scene_desc,
        }
        for scene in scene_meta.scenes
    ]
    scene_meta_json = json.dumps(scene_meta_json, indent=2)

    world_meta = await generate_meta_stage1(
        "world_metadata",
        {
            "SCENES": scene_meta_json,
        },
        world_meta_path,
        pyd.WorldMetadata,
        prompts_dir / "t2t/world_meta.md",
        dependent_paths=[
            scene_requirements_path,
            world_img_meta_path,
            final_img_meta_path,
        ],
        replace=args.replace,
    )

    del scene_meta_json, story_text
    gc.collect()

    subscene_meta = await generate_meta_stage2(
        "subscene_metadata",
        scene_meta,
        subscene_meta_path,
        pyd.SubSceneMetadata,
        prompts_dir / "t2t/subscene_meta.md",
        replace=args.replace,
    )

    character_meta_json = [
        {"char_id": char.char_id, "name": char.name, "role": char.role}
        for char in character_meta.characters
    ]
    prop_meta_json = [
        {
            "prop_id": prop.prop_id,
            "name": prop.name,
        }
        for prop in prop_meta.props
    ]
    world_meta_json = [
        {
            "prop_id": world.world_id,
            "name": world.name,
        }
        for world in world_meta.worlds
    ]

    scene_requirements = await generate_meta_stage3(
        "scene_requirements",
        subscene_meta,
        {
            "STORY_SYNOPSIS": story_meta.synopsis,
            "CHARACTERS": json.dumps(character_meta_json, indent=2),
            "PROPS": json.dumps(prop_meta_json, indent=2),
            "WORLDS": json.dumps(world_meta_json, indent=2),
        },
        scene_requirements_path,
        pyd.SceneIngredientsList,
        prompts_dir / "t2t/scene_requirements.md",
        replace=args.replace,
    )

    del character_meta_json, prop_meta_json, world_meta_json
    gc.collect()

    character_image_prompts, world_image_prompts = await asyncio.gather(
        generate_meta_stage4(
            "character_image_prompts",
            items=character_meta.characters,
            context_inputs={
                "STORY_STYLE": story_meta.story_style,
                "SYNOPSIS": story_meta.synopsis,
            },
            output_path=char_img_meta_path,
            prompts_path=prompts_dir / "t2i/character_create.md",
            id_field="char_id",
            meta_variable="CHAR_META",
            output_schema=pyd.ImagePrompt,
            item_schema=pyd.CharacterImagePrompt,
            list_schema=pyd.CharacterImagePromptList,
            replace=args.replace,
        ),
        generate_meta_stage4(
            "world_image_prompts",
            items=world_meta.worlds,
            context_inputs={
                "STORY_STYLE": story_meta.story_style,
            },
            output_path=world_img_meta_path,
            prompts_path=prompts_dir / "t2i/world_create.md",
            id_field="world_id",
            meta_variable="WORLD_META",
            output_schema=pyd.ImagePrompt,
            item_schema=pyd.WorldImagePrompt,
            list_schema=pyd.WorldImagePromptList,
            replace=args.replace,
        ),
    )

    final_image_prompts = await generate_meta_stage5(
        scene_requirements,
        subscene_meta,
        character_meta,
        prop_meta,
        world_meta,
        story_meta,
        final_img_meta_path,
        prompts_dir / "t2t/process_final_scene.md",
        replace=args.replace,
    )

    del scene_requirements
    del subscene_meta
    del prop_meta
    del world_meta
    del story_meta
    del scene_meta
    gc.collect()

    if not args.skip_image:
        # generate character images
        generate_meta_images(
            character_image_prompts,
            generated_char_images_dir,
            [736, 1280, 1.0, 30],
            "char_id",
        )

        # generate world images
        generate_meta_images(
            world_image_prompts,
            generated_world_images_dir,
            [1920, 1024, 1.0, 30],
            "world_id",
        )

        generate_final_scene_images(
            final_image_prompts,
            character_meta,
            [1920, 1024, 1.0, 30],
            generated_final_images_dir,
            generated_char_images_dir,
            generated_world_images_dir,
            generated_temp_images_dir,
        )


if __name__ == "__main__":
    asyncio.run(main())
