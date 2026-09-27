import argparse
from pathlib import Path

from helper_fn import SUPPORTED_EXTENSIONS, check_story_files
from image_api import IMAGE_BACKENDS


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--story-dir",
        type=str,
        required=True,
        help="Folder in which all the assets created by the program are stored",
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Folder path containing stories (txt, pdf, md, docx, html, epub, etc.)",
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        default=False,
        help="Delete all existing assets and regenerate them fresh",
    )

    parser.add_argument(
        "--skip-image",
        action="store_true",
        default=False,
        help="Skip the image generation stage",
    )

    parser.add_argument(
        "--image-backend",
        choices=IMAGE_BACKENDS,
        default="comfyui",
        help="Image generation backend (comfyui or openrouter)",
    )

    parser.add_argument(
        "--skip-valid",
        action="store_true",
        default=False,
        help="Skip semantic validation of the input files",
    )

    args = parser.parse_args()

    story_dir = Path(args.story_dir).expanduser()
    input_dir = Path(args.input_dir).expanduser()
    prompts_dir = Path("prompts")

    if not story_dir.is_dir():
        raise FileNotFoundError(f"[ERROR] Story directory does not exist: {story_dir}")

    if not input_dir.is_dir():
        raise FileNotFoundError(f"[ERROR] Input directory does not exist: {input_dir}")

    if not check_story_files(input_dir):
        extensions = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise FileNotFoundError(
            f"[ERROR] No supported input files ({extensions}) found in: {input_dir}"
        )

    if not prompts_dir.is_dir():
        raise FileNotFoundError(
            f"[ERROR] Prompts directory does not exist: {prompts_dir}"
        )
    return args
