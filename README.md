# Story2VisualAI

Turn a written story into a fully illustrated, visually consistent scene-by-scene
visual treatment — automatically.

**It costs about a dollar to process an entire book, roughly $0.03 per image —
and the consistency is far better than generating each image in one shot.**

[![Storyboard Examples](https://img.shields.io/badge/%F0%9F%8E%AC%20Storyboard%20Examples-Click%20to%20View-blueviolet?style=for-the-badge)](https://harshitv804.github.io/story2ai/index.html)
[![Apache-2.0 License](https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge)](LICENSE)

Point it at a folder of stories; it reads the prose, understands who and what
appears, breaks each scene into key visual moments, renders a character sheet and
a world plate for every asset, and composes each scene image from those exact
references so faces, outfits, and locations stay identical across the whole story.

## 🧠 How it works

A staged, checkpointed LLM pipeline — each stage produces validated JSON that the
next stage consumes, so every decision is inspectable and resumable:

1. 🔍 **Understand** — extract the story's style, characters, props, and worlds.
2. ✂️ **Structure** — split scenes into sub-scenes (one visual beat each, no
   shot-by-shot coverage).
3. 🎯 **Ground** — map every sub-scene to canonical character / prop / world IDs,
   carrying visual continuity forward within a scene.
4. ✍️ **Prompt** — write image prompts for each character, world, and final scene.
5. 🎨 **Render** — generate character portraits and world plates, then compose each
   scene image by image-to-image from a character reference sheet + world plate.

Output lands in per-story folders: intermediate metadata JSON, character/world
images, final scene images, and multi-page storyboards.

## ✨ Highlights

- 🧍 **Character & world consistency** — final scenes are generated from reference
  images of the exact characters and location, not from text alone.
- 📚 **Asset registries** — the model selects from a fixed asset catalog, so
  characters and props cannot drift, merge, or be invented mid-story.
- 💾 **Resumable** — every stage checkpoints to disk; re-running retries only what
  failed. `--replace` forces a clean rebuild.
- 🔌 **Bring your own models** — any OpenAI-compatible LLM endpoint for reasoning,
  plus ComfyUI (custom workflows) or OpenRouter for image generation.
- 📄 **Format agnostic input** — `.txt`, `.pdf`, `.md`, `.docx`, `.html`, `.epub`,
  `.pptx`.
- 🎞️ **Storyboards** — scenes collected into captioned storyboard pages.

## 📦 Installation

```bash
git clone https://github.com/harshitv804/Story2VisualAI.git
cd Story2VisualAI
pip install -r requirements.txt
```

🧪 Tested on Python 3.12. 🤖 You also need a running ComfyUI instance (with the
bundled Qwen workflows) or an OpenRouter key for image generation, plus your own
OpenAI-compatible LLM endpoint.

## 🚀 Usage

```bash
python src/main.py --story-dir stories/metamorphosis \
                   --input-dir stories/metamorphosis \
                   --image-backend comfyui
```

| Flag | Purpose |
|---|---|
| `--story-dir` | 📁 Where all generated assets are written |
| `--input-dir` | 📖 Folder of source story files |
| `--image-backend` | 🖌️ `comfyui` or `openrouter` |
| `--replace` | 🧹 Delete existing assets and regenerate |
| `--skip-image` | 📝 Metadata/prompts only |
| `--skip-valid` | ⏩ Skip input validation |

⚙️ Configuration is read from `.env.config` / `.env.secrets` (`LLM_API_*`,
`COMFY_URL`, `T2I_WORKFLOW_FILE`, `I2I_WORKFLOW_FILE`, `UNLOAD_WORKFLOW_FILE`,
optional `OPENROUTER_*`).

## 📜 License

Apache-2.0
