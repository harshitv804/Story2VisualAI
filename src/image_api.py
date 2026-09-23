import gc
import json
import math
import os
import time
import uuid
from pathlib import Path

import requests
from config import *
from PIL import Image, ImageDraw, ImageFont


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

    prompt_id = data["prompt_id"]

    print("Queued:", prompt_id)

    return prompt_id


def wait_for_completion(prompt_id):
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

            if status.get("status_str") == "error":
                raise RuntimeError(result)

            if result.get("outputs"):
                return result

            # Some workflows may have no useful image output.
            # In that case, completed status is enough.
            if status.get("completed") is True:
                return result

        time.sleep(1)


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

    prompt_id = submit_workflow(workflow)

    result = wait_for_completion(prompt_id)

    return download_image(
        result,
        output_path,
    )


def generate_image_to_image(
    prompt,
    image_1,
    image_2,
    output_path,
    image_id,
    seed=None,
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

    if seed is None:
        seed = uuid.uuid4().int % (2**32)

    image_1_filename = upload_image(image_1)
    image_2_filename = upload_image(image_2)

    # Character layout
    workflow["477"]["inputs"]["image"] = image_1_filename

    # World image
    workflow["470"]["inputs"]["image"] = image_2_filename

    workflow["459_474"]["inputs"]["prompt"] = prompt

    workflow["459_458"]["inputs"]["seed"] = seed
    workflow["459_458"]["inputs"]["steps"] = steps
    workflow["459_458"]["inputs"]["cfg"] = cfg

    workflow["459_456"]["inputs"]["width"] = width
    workflow["459_456"]["inputs"]["height"] = height

    workflow["479"]["inputs"]["value"] = image_id

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

    prompt_id = submit_workflow(workflow)

    wait_for_completion(prompt_id)
    print()
    print("[IMAGE-GEN] All models have been unloaded")

    gc.collect()


def create_image_layout(data, generated_temp_images_dir):
    if isinstance(data, str):
        data = json.loads(data)

    columns = 3 if len(data) > 3 else 2

    card_width = 300
    image_height = 450
    info_height = 90

    horizontal_gap = 25
    vertical_gap = 25
    margin = 30

    card_height = image_height + info_height

    rows = math.ceil(len(data) / columns)

    canvas_width = margin * 2 + columns * card_width + (columns - 1) * horizontal_gap

    canvas_height = margin * 2 + rows * card_height + (rows - 1) * vertical_gap

    canvas = Image.new(
        "RGB",
        (canvas_width, canvas_height),
        "white",
    )

    draw = ImageDraw.Draw(canvas)

    name_font = ImageFont.load_default(size=25)
    id_font = ImageFont.load_default(size=25)

    for index, item in enumerate(data):
        row = index // columns
        col = index % columns

        x = margin + col * (card_width + horizontal_gap)
        y = margin + row * (card_height + vertical_gap)

        # Card border
        draw.rectangle(
            [x, y, x + card_width, y + card_height],
            outline="black",
            width=2,
        )

        # Image
        image_path = item["image"]

        if os.path.exists(image_path):
            try:
                image = Image.open(image_path)

                image = fit_image(
                    image,
                    (card_width, image_height),
                )

                canvas.paste(image, (x, y))

            except Exception:
                draw.rectangle(
                    [x, y, x + card_width, y + image_height],
                    fill="lightgray",
                )

        else:
            draw.rectangle(
                [x, y, x + card_width, y + image_height],
                fill="lightgray",
            )

            draw.text(
                (x + card_width // 2, y + image_height // 2),
                "IMAGE NOT FOUND",
                fill="black",
                anchor="mm",
            )

        # Separator
        draw.line(
            [x, y + image_height, x + card_width, y + image_height],
            fill="black",
            width=2,
        )

        # Name
        draw.text(
            (x + 15, y + image_height + 15),
            str(item.get("name", "")),
            fill="black",
            font=name_font,
        )

        # ID
        draw.text(
            (x + 15, y + image_height + 50),
            f"ID: {item.get('id', '')}",
            fill="black",
            font=id_font,
        )

    # Save merged image
    output_path = generated_temp_images_dir / "char_merge.png"

    canvas.save(
        output_path,
        format="PNG",
    )

    return output_path


def fit_image(image, size):
    image = image.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)

    background = Image.new("RGB", size, "white")

    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2

    background.paste(image, (x, y))
    return background
