\
from __future__ import annotations

import base64
import json
from urllib.parse import quote

import requests

BASE_TEXT = "https://text.pollinations.ai"
BASE_IMG = "https://image.pollinations.ai"


def _safe_prompt(prompt: str, max_len: int = 2000) -> str:
    prompt = (prompt or "").strip()
    if len(prompt) > max_len:
        prompt = prompt[:max_len]
    return prompt


def generate_text(prompt: str, model: str = "openai", system: str | None = None, timeout: int = 90, max_len: int = 2000) -> str:
    prompt = _safe_prompt(prompt, max_len=max_len)
    if not prompt:
        return "Пустой запрос. Пример: /text Придумай контент-план на неделю"
    url = f"{BASE_TEXT}/{quote(prompt)}"
    params: dict[str, object] = {"model": model}
    if system:
        params["system"] = system
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.text.strip()


def generate_image_bytes(
    prompt: str,
    *,
    model: str = "flux",
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    timeout: int = 120,
    max_len: int = 2000,
    image_bytes: bytes | None = None,
) -> bytes:
    """
    If image_bytes is provided, we send it as base64 in a query param.
    Pollinations supports basic image-to-image via 'image' param for some backends.
    If a backend doesn't support it, generation will still succeed as text-to-image.
    """
    prompt = _safe_prompt(prompt, max_len=max_len)
    if not prompt:
        raise ValueError("Пустой запрос для картинки.")

    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode("ascii")
        # Keep payload smaller; if image is too large, consider resizing/compressing before calling.
        img_b64 = img_b64[:150000]
        url = f"{BASE_IMG}/prompt/{quote(prompt)}"
        params: dict[str, object] = {"model": model, "width": width, "height": height, "image": img_b64}
    else:
        url = f"{BASE_IMG}/prompt/{quote(prompt)}"
        params = {"model": model, "width": width, "height": height}

    if seed is not None:
        params["seed"] = seed

    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.content
