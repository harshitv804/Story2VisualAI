import base64
import gc
import json
import math
import mimetypes
import os
import time
import uuid
from pathlib import Path

import requests
from config import (
    COMFY_URL,
    I2I_WORKFLOW_FILE,
    OPENROUTER_API_KEY,
    OPENROUTER_APP_TITLE,
    OPENROUTER_IMAGE_BACKGROUND,
    OPENROUTER_IMAGE_MODEL_ID,
    OPENROUTER_IMAGE_OUTPUT_FORMAT,
    OPENROUTER_IMAGE_QUALITY,
    OPENROUTER_IMAGES_URL,
    OPENROUTER_SITE_URL,
    T2I_WORKFLOW_FILE,
    UNLOAD_WORKFLOW_FILE,
)
from PIL import Image, ImageDraw, ImageFont

IMAGE_BACKENDS = ("comfyui", "openrouter")

# Character sheets are portrait, worlds and final scenes are landscape
PORTRAIT_ASPECT_RATIO = "3:4"
LANDSCAPE_ASPECT_RATIO = "16:9"


def submit_workflow(workflow):
    response = requests.post(
        f"{COMFY_URL}/prompt",
        json={
            "prompt": workflow,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(data)

    return data["prompt_id"]


def interrupt_comfyui():
    """Interrupt the currently running ComfyUI job."""
    try:
        response = requests.post(
            f"{COMFY_URL}/interrupt",
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[IMAGE-WARN] Failed to interrupt ComfyUI: {e}")


def wait_for_completion(prompt_id):
    try:
        while True:
            response = requests.get(
                f"{COMFY_URL}/history/{prompt_id}",
                timeout=30,
            )

            response.raise_for_status()

            history = response.json()

            if prompt_id in history:
                result = history[prompt_id]

                status = result.get("status", {})

                # ComfyUI reported an execution error
                if status.get("status_str") == "error":
                    print(f"[IMAGE-GEN] ComfyUI failed: {prompt_id}")

                    interrupt_comfyui()

                    raise RuntimeError(result)

                # Completed successfully with outputs
                if result.get("outputs"):
                    return result

                # Completed successfully without outputs
                if status.get("completed") is True:
                    return result

            time.sleep(1)

    except KeyboardInterrupt:
        # User pressed Ctrl+C
        print("[IMAGE-GEN] Manual interrupt requested")

        interrupt_comfyui()

        # Keep KeyboardInterrupt behavior so the caller knows
        # the generation was manually cancelled.
        raise

    except Exception as e:
        # Any unexpected Python/network/etc. failure
        print(f"[IMAGE-GEN] Waiting for ComfyUI failed: {e}")

        interrupt_comfyui()

        raise


def download_image(result, output_path):
    for node_id, output in result.get("outputs", {}).items():
        if "images" not in output:
            continue

        for image in output["images"]:
            response = requests.get(
                f"{COMFY_URL}/view",
                params={
                    "filename": image["filename"],
                    "subfolder": image["subfolder"],
                    "type": image["type"],
                },
                timeout=60,
            )

            response.raise_for_status()

            output_path = Path(output_path)
            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with open(output_path, "wb") as f:
                f.write(response.content)

            return output_path

    raise RuntimeError("No image found in ComfyUI output")


def upload_image(image_path):
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(image_path, "rb") as f:
        response = requests.post(
            f"{COMFY_URL}/upload/image",
            files={
                "image": (
                    image_path.name,
                    f,
                    "application/octet-stream",
                )
            },
            data={
                "overwrite": "true",
            },
            timeout=60,
        )

    response.raise_for_status()

    data = response.json()

    if data.get("error"):
        raise RuntimeError(data)

    return data["name"]


def generate_text_to_image(
    prompt,
    output_path,
    image_id,
    seed=None,
    steps=30,
    cfg=2.0,
    width=732,
    height=1280,
):

    with open(
        T2I_WORKFLOW_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        workflow = json.load(f)

    if seed is None:
        seed = uuid.uuid4().int % (2**32)

    # Prompt
    workflow["459_452"]["inputs"]["prompt"] = prompt
    # KSampler
    workflow["459_458"]["inputs"]["seed"] = seed
    workflow["459_458"]["inputs"]["steps"] = steps
    workflow["459_458"]["inputs"]["cfg"] = cfg

    # Resolution
    workflow["459_456"]["inputs"]["width"] = width
    workflow["459_456"]["inputs"]["height"] = height

    workflow["462"]["inputs"]["value"] = image_id

    print(
        f"[IMAGE-API] {image_id}: request -> comfyui "
        f"({width}x{height}, cfg {cfg}, steps {steps})"
    )

    prompt_id = submit_workflow(workflow)

    result = wait_for_completion(prompt_id)

    return download_image(
        result,
        output_path,
    )


def generate_image_to_image(
    prompt,
    char_layout_1,
    char_layout_2,
    world_image,
    output_path,
    image_id,
    steps=25,
    cfg=2.0,
    width=1280,
    height=720,
):
    with open(
        I2I_WORKFLOW_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        workflow = json.load(f)

    seed = uuid.uuid4().int % (2**32)

    # UPLOAD CHARACTER LAYOUT 1
    image_1_filename = upload_image(char_layout_1)

    # UPLOAD CHARACTER LAYOUT 2
    image_2_filename = upload_image(char_layout_2)

    # UPLOAD WORLD IMAGE
    world_filename = upload_image(world_image)

    # SET WORKFLOW IMAGE INPUTS
    # Character layout 1 -> node 477
    workflow["477"]["inputs"]["image"] = image_1_filename

    # Character layout 2 -> node 480
    workflow["480"]["inputs"]["image"] = image_2_filename

    # World image -> node 470
    workflow["470"]["inputs"]["image"] = world_filename

    # SET PROMPTS
    workflow["459_474"]["inputs"]["prompt"] = prompt

    # SET SAMPLER
    workflow["459_458"]["inputs"]["seed"] = seed

    workflow["459_458"]["inputs"]["steps"] = steps

    workflow["459_458"]["inputs"]["cfg"] = cfg

    workflow["459_456"]["inputs"]["width"] = width

    workflow["459_456"]["inputs"]["height"] = height

    workflow["479"]["inputs"]["value"] = image_id

    print(
        f"[IMAGE-API] {image_id}: request -> comfyui "
        f"({width}x{height}, cfg {cfg}, steps {steps}, 3 references)"
    )

    prompt_id = submit_workflow(workflow)

    result = wait_for_completion(prompt_id)

    return download_image(
        result,
        output_path,
    )


def unload_models():

    with open(
        UNLOAD_WORKFLOW_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        workflow = json.load(f)

    print("[IMAGE-API] unload: request -> comfyui")

    prompt_id = submit_workflow(workflow)

    wait_for_completion(prompt_id)
    print("[IMAGE-API] unload: models unloaded")

    gc.collect()


def encode_image(image_path) -> dict:
    image_path = Path(image_path)

    media_type = mimetypes.guess_type(image_path.name)[0] or "image/png"

    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    return {
        "type": "image_url",
        "image_url": {"url": f"data:{media_type};base64,{encoded}"},
    }


def save_openrouter_result(response_json, output_path):
    data = response_json.get("data") or []

    if not data:
        raise RuntimeError(f"[ERROR] No image returned -> {response_json}")

    image = data[0]

    if image.get("b64_json"):
        image_bytes = base64.b64decode(image["b64_json"])
    elif image.get("url"):
        download = requests.get(image["url"], timeout=120)
        download.raise_for_status()
        image_bytes = download.content
    else:
        raise RuntimeError(f"[ERROR] Unexpected image payload -> {image}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    return output_path


def openrouter_image_request(
    prompt,
    output_path,
    image_id,
    aspect_ratio,
    resolution="1K",
    references=None,
    n=1,
):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("[ERROR] OPENROUTER_API_KEY is not set")

    if not OPENROUTER_IMAGE_MODEL_ID:
        raise RuntimeError("[ERROR] OPENROUTER_IMAGE_MODEL_ID is not set")

    payload = {
        "model": OPENROUTER_IMAGE_MODEL_ID,
        "prompt": prompt,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "n": n,
        "quality": OPENROUTER_IMAGE_QUALITY,
        "output_format": OPENROUTER_IMAGE_OUTPUT_FORMAT,
        "background": OPENROUTER_IMAGE_BACKGROUND,
    }

    if references:
        payload["input_references"] = references

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL

    if OPENROUTER_APP_TITLE:
        headers["X-Title"] = OPENROUTER_APP_TITLE

    print(
        f"[IMAGE-API] {image_id}: request -> {OPENROUTER_IMAGE_MODEL_ID} "
        f"({payload['aspect_ratio']}, {resolution})"
    )

    response = requests.post(
        OPENROUTER_IMAGES_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=900,
    )

    if not response.ok:
        raise RuntimeError(
            f"[ERROR] {image_id}: {response.status_code} -> {response.text[:500]}"
        )

    return save_openrouter_result(response.json(), output_path)


def generate_text_to_image_openrouter(
    prompt,
    output_path,
    image_id,
    aspect_ratio=LANDSCAPE_ASPECT_RATIO,
    resolution="1K",
):
    return openrouter_image_request(
        prompt,
        output_path,
        image_id,
        aspect_ratio,
        resolution=resolution,
    )


def generate_image_to_image_openrouter(
    prompt,
    char_layout_1,
    char_layout_2,
    world_image,
    output_path,
    image_id,
    aspect_ratio=LANDSCAPE_ASPECT_RATIO,
    resolution="1K",
):
    references = [
        encode_image(path)
        for path in (
            char_layout_1,
            char_layout_2,
            world_image,
        )
    ]

    return openrouter_image_request(
        prompt,
        output_path,
        image_id,
        aspect_ratio,
        resolution=resolution,
        references=references,
    )


def text_to_image(
    backend,
    prompt,
    output_path,
    image_id,
    width,
    height,
    cfg,
    steps,
    aspect_ratio=LANDSCAPE_ASPECT_RATIO,
    resolution="1K",
):
    if backend not in IMAGE_BACKENDS:
        raise ValueError(
            f"[ERROR] Unknown image backend '{backend}' "
            f"(expected one of {', '.join(IMAGE_BACKENDS)})"
        )

    if backend == "openrouter":
        return generate_text_to_image_openrouter(
            prompt,
            output_path,
            image_id,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

    return generate_text_to_image(
        prompt=prompt,
        output_path=output_path,
        image_id=image_id,
        width=width,
        height=height,
        cfg=cfg,
        steps=steps,
    )


def image_to_image(
    backend,
    prompt,
    char_layout_1,
    char_layout_2,
    world_image,
    output_path,
    image_id,
    width,
    height,
    cfg,
    steps,
    aspect_ratio=LANDSCAPE_ASPECT_RATIO,
    resolution="1K",
):
    if backend not in IMAGE_BACKENDS:
        raise ValueError(
            f"[ERROR] Unknown image backend '{backend}' "
            f"(expected one of {', '.join(IMAGE_BACKENDS)})"
        )

    if backend == "openrouter":
        return generate_image_to_image_openrouter(
            prompt=prompt,
            char_layout_1=char_layout_1,
            char_layout_2=char_layout_2,
            world_image=world_image,
            output_path=output_path,
            image_id=image_id,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

    return generate_image_to_image(
        prompt=prompt,
        char_layout_1=char_layout_1,
        char_layout_2=char_layout_2,
        world_image=world_image,
        output_path=output_path,
        image_id=image_id,
        width=width,
        height=height,
        cfg=cfg,
        steps=steps,
    )


def unload_backend(backend):
    if backend == "comfyui":
        unload_models()


def create_image_layout(
    data,
    generated_temp_images_dir,
):
    
    # ALWAYS USE THESE TWO FILENAMES
    layout_1_path = generated_temp_images_dir / "char_merge1.png"
    layout_2_path = generated_temp_images_dir / "char_merge2.png"

    # NO CHARACTERS
    if not data:
        empty_canvas = Image.new(
            "RGB",
            (300, 450),
            "white",
        )

        empty_canvas.save(layout_1_path)
        empty_canvas.save(layout_2_path)

        return layout_1_path, layout_2_path

    # SPLIT CHARACTERS AS EQUALLY AS POSSIBLE
    # 1 -> 1 + 0
    # 2 -> 1 + 1
    # 3 -> 2 + 1
    # 4 -> 2 + 2
    # 5 -> 3 + 2
    # 6 -> 3 + 3

    total_chars = len(data)

    chars_in_layout_1 = math.ceil(total_chars / 2)

    chunk_1 = data[:chars_in_layout_1]
    chunk_2 = data[chars_in_layout_1:]

    chunks = [
        chunk_1,
        chunk_2,
    ]

    layout_paths = [
        layout_1_path,
        layout_2_path,
    ]

    # CREATE BOTH LAYOUTS
    for layout_index, chunk in enumerate(chunks):
        output_path = layout_paths[layout_index]

        # EMPTY LAYOUT
        if not chunk:
            empty_canvas = Image.new(
                "RGB",
                (300, 450),
                "white",
            )

            empty_canvas.save(output_path)

            continue

        # LAYOUT SIZE
        columns = 3 if len(chunk) == 3 else len(chunk)

        card_width = 300
        image_height = 450
        info_height = 90

        horizontal_gap = 25
        vertical_gap = 25
        margin = 30

        card_height = image_height + info_height

        rows = math.ceil(len(chunk) / columns)

        canvas_width = (
            margin * 2 + columns * card_width + (columns - 1) * horizontal_gap
        )

        canvas_height = margin * 2 + rows * card_height + (rows - 1) * vertical_gap

        canvas = Image.new(
            "RGB",
            (canvas_width, canvas_height),
            "white",
        )

        draw = ImageDraw.Draw(canvas)

        name_font = ImageFont.load_default(size=25)
        id_font = ImageFont.load_default(size=25)

        # ADD CHARACTER CARDS
        for index, item in enumerate(chunk):
            row = index // columns
            col = index % columns

            x = margin + col * (card_width + horizontal_gap)

            y = margin + row * (card_height + vertical_gap)

            # Card border
            draw.rectangle(
                [
                    x,
                    y,
                    x + card_width,
                    y + card_height,
                ],
                outline="black",
                width=2,
            )

            image_path = item["image"]

            if os.path.exists(image_path):
                try:
                    image = Image.open(image_path).convert("RGB")

                    image = fit_image(
                        image,
                        (card_width, image_height),
                    )

                    canvas.paste(
                        image,
                        (x, y),
                    )

                except Exception:
                    draw.rectangle(
                        [
                            x,
                            y,
                            x + card_width,
                            y + image_height,
                        ],
                        fill="lightgray",
                    )

            else:
                draw.rectangle(
                    [
                        x,
                        y,
                        x + card_width,
                        y + image_height,
                    ],
                    fill="lightgray",
                )

                draw.text(
                    (
                        x + card_width // 2,
                        y + image_height // 2,
                    ),
                    "IMAGE NOT FOUND",
                    fill="black",
                    anchor="mm",
                )

            # Separator
            draw.line(
                [
                    x,
                    y + image_height,
                    x + card_width,
                    y + image_height,
                ],
                fill="black",
                width=2,
            )

            # Character name
            draw.text(
                (
                    x + 15,
                    y + image_height + 15,
                ),
                str(item.get("name", "")),
                fill="black",
                font=name_font,
            )

            # Character ID
            draw.text(
                (
                    x + 15,
                    y + image_height + 50,
                ),
                f"{item.get('id', '')}",
                fill="black",
                font=id_font,
            )

        # SAVE / OVERWRITE
        canvas.save(output_path)

    return layout_1_path, layout_2_path


def fit_image(image, size):
    if image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail(
        size,
        Image.Resampling.LANCZOS,
    )

    background = Image.new(
        "RGB",
        size,
        "white",
    )

    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2

    background.paste(
        image,
        (x, y),
    )

    return background
