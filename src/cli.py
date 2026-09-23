import argparse
from pathlib import Path

from helper_fn import check_story_files


def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--story-dir",
        type=str,
        required=True,
        help="Folder path in which all the assests created by the program will be stored",
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
        help="Delete all existing the existing assets and regenerate fresh",
    )

    parser.add_argument(
        "--skip-image",
        action="store_true",
        default=False,
        help="Skip the image generation stage",
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
    else:
        if not check_story_files(input_dir):
            raise FileNotFoundError(
                f"[ERROR] No supported input files {('.txt', '.pdf', '.md', '.docx', '.html', '.epub')} found in: {input_dir}"
            )

    if not prompts_dir.is_dir():
        raise FileNotFoundError(
            f"[ERROR] Prompts directory does not exist: {prompts_dir}"
        )
    return args
