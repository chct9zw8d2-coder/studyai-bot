from __future__ import annotations

import requests
from urllib.parse import quote

BASE_TEXT = "https://text.pollinations.ai"
BASE_IMG = "https://image.pollinations.ai"

def _safe_prompt(prompt: str, max_len: int = 2000) -> str:
    prompt = (prompt or "").strip()
    if len(prompt) > max_len:
        prompt = prompt[:max_len]
    return prompt

def generate_text(prompt: str, *, model: str = "openai", system: str | None = None,
                  temperature: float | None = None, timeout: int = 90, max_len: int = 2000) -> str:
    prompt = _safe_prompt(prompt, max_len=max_len)
    if not prompt:
        return "Пустой запрос. Пример: /text Придумай контент-план на неделю"
    url = f"{BASE_TEXT}/{quote(prompt)}"
    params: dict[str, object] = {"model": model}
    if system:
        params["system"] = system
    if temperature is not None:
        params["temperature"] = temperature
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.text.strip()

def generate_image_bytes(prompt: str, *, model: str = "flux", width: int = 1024, height: int = 1024,
                         seed: int | None = None, enhance: bool = True, timeout: int = 90, max_len: int = 2000) -> bytes:
    prompt = _safe_prompt(prompt, max_len=max_len)
    if not prompt:
        raise ValueError("Пустой запрос для картинки.")
    url = f"{BASE_IMG}/prompt/{quote(prompt)}"
    params: dict[str, object] = {"model": model, "width": width, "height": height}
    if seed is not None:
        params["seed"] = seed
    if enhance:
        params["enhance"] = "true"
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.content
