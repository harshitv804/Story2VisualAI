import os

from dotenv import load_dotenv

load_dotenv(".env.secrets")
load_dotenv(".env.config")

if not os.getenv("LLM_API_KEY"):
    raise ValueError("LLM_API_KEY is not set")

if not os.getenv("LLM_API_BASE_URL"):
    raise ValueError("LLM_API_BASE_URL is not set")

if not os.getenv("LLM_API_MODEL_ID"):
    raise ValueError("LLM_API_MODEL_ID is not set")

if not os.getenv("COMFY_URL"):
    raise ValueError("COMFY_URL is not set")

if not os.getenv("T2I_WORKFLOW_FILE"):
    raise ValueError("T2I_WORKFLOW_FILE is not set")

if not os.getenv("I2I_WORKFLOW_FILE"):
    raise ValueError("I2I_WORKFLOW_FILE is not set")

if not os.getenv("UNLOAD_WORKFLOW_FILE"):
    raise ValueError("UNLOAD_WORKFLOW_FILE is not set")

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL")
LLM_API_MODEL_ID = os.getenv("LLM_API_MODEL_ID")

COMFY_URL = os.getenv("COMFY_URL")
T2I_WORKFLOW_FILE = os.getenv("T2I_WORKFLOW_FILE")
I2I_WORKFLOW_FILE = os.getenv("I2I_WORKFLOW_FILE")
UNLOAD_WORKFLOW_FILE = os.getenv("UNLOAD_WORKFLOW_FILE")

# Image generation via the OpenRouter images API (optional, same key as the LLM)
OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or LLM_API_KEY
OPENROUTER_IMAGE_MODEL_ID = os.getenv(
    "OPENROUTER_IMAGE_MODEL_ID",
    "qwen/qwen-image-3",
)
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL")
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE")
OPENROUTER_IMAGE_QUALITY = os.getenv("OPENROUTER_IMAGE_QUALITY", "high")
OPENROUTER_IMAGE_OUTPUT_FORMAT = os.getenv(
    "OPENROUTER_IMAGE_OUTPUT_FORMAT",
    "png",
)
OPENROUTER_IMAGE_BACKGROUND = os.getenv("OPENROUTER_IMAGE_BACKGROUND", "opaque")
