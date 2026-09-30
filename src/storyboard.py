import json
import math
import re
import sys
from pathlib import Path

import pydantic_models as pyd
from PIL import Image, ImageDraw, ImageFont

# ==================================================
# PAGE LAYOUT DEFAULTS
# ==================================================

PAGE_SIZE = (1920, 1080)
PAGE_MARGIN = 36
COLUMN_GAP = 40
ROW_GAP = 24
TEXT_GAP = 24
COLUMNS_PER_PAGE = 2
ROWS_PER_PAGE = 2
TEXT_LINE_HEIGHT = 32
TEXT_FONT_SIZE = 24
HEADER_FONT_SIZE = 28

# Fixed text band so every page keeps the same frame size
TEXT_RESERVED_LINES = 5
TEXT_BAND_HEIGHT = TEXT_RESERVED_LINES * TEXT_LINE_HEIGHT

BACKGROUND_COLOR = "black"
TEXT_COLOR = "white"
HEADER_COLOR = "white"
HEADER_HEIGHT = 48


def load_scenes(scene_meta_path: Path) -> pyd.SceneMetadata:
    existing = json.loads(scene_meta_path.read_text(encoding="utf-8"))

    return pyd.SceneMetadata.model_validate(existing)


def group_subscene_images(final_images_dir: Path, scene_ids: list[str]):
    """Group final_images/<scene_id><letter>.png under their scene, in order."""

    images_by_scene = {scene_id: [] for scene_id in scene_ids}

    for image_path in sorted(final_images_dir.glob("*.png")):
        stem = image_path.stem

        # Longest match wins so 'S25A' is not claimed by scene 'S2'
        matches = [
            scene_id
            for scene_id in scene_ids
            if stem.startswith(scene_id)
            and re.fullmatch(r"[A-Za-z]*", stem[len(scene_id) :])
        ]

        if not matches:
            print(f"[BOARD-WARN] No scene matches -> '{image_path.name}'")
            continue

        scene_id = max(matches, key=len)

        images_by_scene[scene_id].append((stem[len(scene_id) :], image_path))

    for entries in images_by_scene.values():
        entries.sort(key=lambda entry: entry[0])

    return images_by_scene


def image_ratio(image_path: Path):
    if not image_path.exists():
        return None

    with Image.open(image_path) as image:
        return image.height / image.width


def first_image_ratio(columns: list[dict]):
    for column in columns:
        for image_path in column["images"]:
            ratio = image_ratio(image_path)

            if ratio:
                return ratio

    return 9 / 16


def frame_size(column_width: int, ratio: float):
    """One fixed frame size used by every page, based on ROWS_PER_PAGE."""

    page_width, page_height = PAGE_SIZE

    content_height = page_height - 2 * PAGE_MARGIN - HEADER_HEIGHT

    height = (
        content_height
        - (ROWS_PER_PAGE - 1) * ROW_GAP
        - 2 * TEXT_GAP
        - TEXT_BAND_HEIGHT
    ) // ROWS_PER_PAGE

    return column_width, min(height, int(column_width * ratio))


def wrap_words(draw, text: str, font, max_width: int, max_lines: int):
    """Split text into lines of words that fit within max_width."""

    lines = []
    current = []

    for word in str(text).split():
        candidate = current + [word]

        if draw.textlength(" ".join(candidate), font=font) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)

        current = [word]

    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1] + ["..."]

    return lines


def draw_justified_text(draw, lines, font, left: int, top: int, width: int):
    """Draw lines justified to width, keeping the last line flush left."""

    last_index = len(lines) - 1

    for index, words in enumerate(lines):
        if not words:
            continue

        if index == last_index or len(words) == 1:
            draw.text(
                (left, top + index * TEXT_LINE_HEIGHT),
                " ".join(words),
                fill=TEXT_COLOR,
                font=font,
            )
            continue

        words_width = sum(draw.textlength(word, font=font) for word in words)

        gap = max(0.0, (width - words_width) / (len(words) - 1))

        cursor = float(left)

        for word in words:
            draw.text(
                (cursor, top + index * TEXT_LINE_HEIGHT),
                word,
                fill=TEXT_COLOR,
                font=font,
            )
            cursor += draw.textlength(word, font=font) + gap


def fit_into(image, size):
    image = image.convert("RGB")

    scale = min(size[0] / image.width, size[1] / image.height)

    return image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.Resampling.LANCZOS,
    )


def create_storyboard_page(
    page_columns: list[dict],
    output_path: Path,
    cell_size: tuple[int, int],
    page_number: int,
    page_total: int,
):
    page_width, page_height = PAGE_SIZE

    page = Image.new("RGB", PAGE_SIZE, BACKGROUND_COLOR)

    draw = ImageDraw.Draw(page)

    text_font = ImageFont.load_default(size=TEXT_FONT_SIZE)
    header_font = ImageFont.load_default(size=HEADER_FONT_SIZE)

    cell_width, cell_height = cell_size

    rows = max(len(column["images"]) for column in page_columns)

    # Rows split around the text band so it sits between the subscenes
    rows_above = math.ceil(rows / 2)

    content_top = PAGE_MARGIN + HEADER_HEIGHT

    content_height = page_height - 2 * PAGE_MARGIN - HEADER_HEIGHT

    block_height = (
        rows * cell_height
        + (rows - 1) * ROW_GAP
        + 2 * TEXT_GAP
        + TEXT_BAND_HEIGHT
    )

    block_top = content_top + max(0, (content_height - block_height) // 2)

    text_top = (
        block_top
        + rows_above * cell_height
        + max(0, rows_above - 1) * ROW_GAP
        + TEXT_GAP
    )

    draw.text(
        (PAGE_MARGIN, PAGE_MARGIN),
        f"{page_number} / {page_total}",
        fill=HEADER_COLOR,
        font=header_font,
    )

    for column_index, column in enumerate(page_columns):
        left = PAGE_MARGIN + column_index * (cell_width + COLUMN_GAP)

        for row_index, image_path in enumerate(column["images"]):
            if row_index < rows_above:
                cell_top = block_top + row_index * (cell_height + ROW_GAP)
            else:
                cell_top = (
                    text_top
                    + TEXT_BAND_HEIGHT
                    + TEXT_GAP
                    + (row_index - rows_above) * (cell_height + ROW_GAP)
                )

            if not image_path.exists():
                print(f"[BOARD-WARN] Image missing -> '{image_path}'")
                continue

            with Image.open(image_path) as source:
                image = fit_into(source, (cell_width, cell_height))

            offset_x = left + (cell_width - image.width) // 2
            offset_y = cell_top + (cell_height - image.height) // 2

            page.paste(image, (offset_x, offset_y))

        text_lines = wrap_words(
            draw,
            column["scene_desc"],
            text_font,
            cell_width,
            TEXT_RESERVED_LINES,
        )

        draw_justified_text(
            draw,
            text_lines,
            text_font,
            left,
            text_top,
            cell_width,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.save(output_path, format="PNG")

    return output_path


def build_pages(scenes: list[dict]):
    """Split scenes into page columns, continuing long scenes on the next page."""

    columns = []

    for scene in scenes:
        images = scene["images"]

        chunks = [
            images[start : start + ROWS_PER_PAGE]
            for start in range(0, len(images), ROWS_PER_PAGE)
        ]

        if len(chunks) > 1:
            print(
                f"[BOARD-NOTE] {scene['scene_id']} has {len(images)} subscenes, "
                f"continuing on the next page"
            )

        for index, chunk in enumerate(chunks):
            columns.append(
                {
                    "scene_id": scene["scene_id"],
                    # Text only on the first chunk of a scene
                    "scene_desc": scene["scene_desc"] if index == 0 else "",
                    "images": chunk,
                }
            )

    return [
        columns[i : i + COLUMNS_PER_PAGE]
        for i in range(0, len(columns), COLUMNS_PER_PAGE)
    ]


def create_storyboards(
    scene_meta_path: Path,
    final_images_dir: Path,
    output_dir: Path,
) -> list[Path]:

    print()
    print(f"[BOARD] Reading scenes -> '{scene_meta_path}'")

    scene_meta = load_scenes(scene_meta_path)

    scene_ids = [scene.scene_id for scene in (scene_meta.scenes or [])]

    if not scene_ids:
        raise RuntimeError(f"[ERROR] No scenes found -> '{scene_meta_path}'")

    images_by_scene = group_subscene_images(final_images_dir, scene_ids)

    scenes = [
        {
            "scene_id": scene.scene_id,
            "scene_desc": scene.scene_desc,
            "images": [
                image_path for _, image_path in images_by_scene[scene.scene_id]
            ],
        }
        for scene in (scene_meta.scenes or [])
    ]

    pages = build_pages(scenes)

    page_width, _ = PAGE_SIZE

    column_width = (page_width - 2 * PAGE_MARGIN - COLUMN_GAP) // COLUMNS_PER_PAGE

    # One frame size for every page, so pages stay visually consistent
    cell_size = frame_size(column_width, first_image_ratio(scenes))

    total = len(pages)

    print(
        f"[BOARD] {len(scenes)} scenes -> {total} page(s) "
        f"(frame {cell_size[0]}x{cell_size[1]})"
    )

    output_paths = []

    for page_index, page_columns in enumerate(pages, start=1):
        page_path = output_dir / f"storyboard_{page_index:02d}.png"

        create_storyboard_page(
            page_columns,
            page_path,
            cell_size,
            page_index,
            total,
        )

        print(
            f"[BOARD-SAVED] page {page_index}/{total} -> '{page_path}' "
            f"({', '.join(column['scene_id'] for column in page_columns)})"
        )

        output_paths.append(page_path)

    print(f"[BOARD-DONE] {len(output_paths)} page(s) -> '{output_dir}'")

    return output_paths


if __name__ == "__main__":
    story_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "stories/metamorphosis")

    create_storyboards(
        story_dir / "generated_metadata" / "scenes_metadata.json",
        story_dir / "generated_output" / "final_images",
        story_dir / "generated_output" / "storyboards",
    )
