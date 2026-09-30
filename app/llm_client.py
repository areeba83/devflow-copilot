"""
Thin wrapper around the local Ollama runtime — text-only and multimodal.
Keeping this as the one place that calls the model is what SRS Section 11
means by isolating the model call: later days, or a model swap, never
require touching main.py or any prompt file.

Requires: `ollama serve` running locally, and both models already pulled:
    ollama pull qwen2.5:7b          # text model (adjust size to hardware)
    ollama pull qwen2.5vl:7b        # vision model, for Day 2 image input
                                     # (also adjust size to hardware, or try
                                     # llava if a Qwen vision tag isn't
                                     # available on your Ollama version)
"""

import os
import ollama

DEFAULT_MODEL = os.environ.get("DEVFLOW_MODEL", "qwen2.5:7b")
VISION_MODEL = os.environ.get("DEVFLOW_VISION_MODEL", "qwen2.5vl:7b")


class LLMError(Exception):
    """Raised when the local model can't be reached or fails to respond.
    Callers must catch this and return a structured model_error result —
    never let it crash the request (SRS: 'graceful failure handling')."""


def generate_raw(prompt: str, model_name: str = DEFAULT_MODEL) -> str:
    try:
        response = ollama.generate(model=model_name, prompt=prompt)
    except Exception as e:
        # Covers: ollama not running, model not pulled, connection refused.
        raise LLMError(
            f"Could not get a response from local model '{model_name}'. "
            f"Is `ollama serve` running and is the model pulled? "
            f"Underlying error: {e}"
        ) from e

    text = response.get("response", "").strip()
    if not text:
        raise LLMError(f"Model '{model_name}' returned an empty response.")
    return text


def generate_raw_with_images(prompt: str, image_paths: list[str],
                              model_name: str = VISION_MODEL) -> str:
    """Day 2: same contract as generate_raw, but sends one or more local
    image file paths alongside the prompt to a vision-capable model.
    `ollama-python` accepts local file paths directly in `images` and
    base64-encodes them internally."""
    if not image_paths:
        raise LLMError("generate_raw_with_images called with no images.")

    try:
        response = ollama.generate(model=model_name, prompt=prompt, images=image_paths)
    except Exception as e:
        raise LLMError(
            f"Could not get a response from vision model '{model_name}'. "
            f"Is it pulled (`ollama pull {model_name}`) and is `ollama serve` "
            f"running? Underlying error: {e}"
        ) from e

    text = response.get("response", "").strip()
    if not text:
        raise LLMError(f"Vision model '{model_name}' returned an empty response.")
    return text
