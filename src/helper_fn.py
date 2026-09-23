from pathlib import Path

from markitdown import MarkItDown


def check_story_files(input_dir: Path) -> bool:
    extensions = {".txt", ".pdf", ".md", ".docx", ".html", ".epub"}

    return any(
        path.is_file() and path.suffix.lower() in extensions
        for path in input_dir.iterdir()
    )


def preprocess_input(input_dir: Path, output_path: Path, replace: bool = False) -> None:

    print()
    if output_path.exists() and not replace:
        print(f"[SKIP] Using existing processed input -> '{output_path}'")
        return

    else:
        md = MarkItDown()

        supported_extensions = {
            ".txt",
            ".pdf",
            ".docx",
            ".html",
            ".md",
            ".epub",
            ".pptx",
        }

        # Make sure the output directory exists.
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Find supported files.
        files = sorted(
            (
                path
                for path in input_dir.rglob("*")
                if path.is_file()
                and path.suffix.lower() in supported_extensions
                and path.resolve() != output_path.resolve()
            ),
            key=lambda path: str(path).lower(),
        )

        print(f"[INFO] Found {len(files)} file(s) in -> '{input_dir}'")

        files_count = 0
        chars_count = 0

        # Create/overwrite the output file once.
        with output_path.open("w", encoding="utf-8") as output_file:
            for file_path in files:
                print(f"[PRE-PROCESS] Converting file -> '{file_path}'")

                try:
                    result = md.convert(str(file_path))
                    text = (result.text_content or "").strip()

                    if not text:
                        raise ValueError("[ERROR] MarkItDown returned empty content")

                except Exception as e:
                    raise RuntimeError(
                        f"[ERROR] Failed to preprocess -> '{file_path}'"
                    ) from e

                # Write each file immediately.
                output_file.write(text)
                output_file.write("\n")

                files_count += 1
                chars_count += len(text)

        print(
            f"[SAVED] Preprocessed input -> '{output_path}' "
            f"({chars_count} chars, {files_count} files)"
        )


def load_processed_input(input_file_path: Path) -> str:

    print(f"[READING-FILE] -> '{input_file_path}'")
    try:
        story_text = input_file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(
            f"[ERROR] Failed to read combined_input.md -> '{input_file_path}'"
        ) from e

    if not story_text.strip():
        raise ValueError(
            f"[ERROR] File combined_input.md is empty -> '{input_file_path}'"
        )
    else:
        print(f"[INFO] {len(story_text)} chars loaded from -> '{input_file_path}'")
        return story_text


def read_md(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def has_json_data(value) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, list):
        return any(has_json_data(item) for item in value)

    if isinstance(value, dict):
        return any(has_json_data(v) for v in value.values())

    # numbers, booleans, etc.
    return True
