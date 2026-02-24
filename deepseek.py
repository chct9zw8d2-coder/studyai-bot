import base64
from typing import Optional

import requests

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_VISION_MODEL,
    DEEPSEEK_BASE_URL,
)


def generate_text(prompt: str, system: Optional[str] = None, max_tokens: int = 900, model: Optional[str] = None) -> str:
    """Text-only requests via DeepSeek (OpenAI-compatible /chat/completions)."""
    if not DEEPSEEK_API_KEY:
        return "⚠️ DeepSeek API key is not configured."

    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": (model or DEEPSEEK_MODEL),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


def generate_vision(
    prompt: str,
    image_bytes: bytes,
    mime: str = "image/jpeg",
    system: Optional[str] = None,
    max_tokens: int = 1200,
) -> str:
    """Image analysis (e.g., checking a photo of homework).

    We send the image as a base64 data URL in an OpenAI-compatible message format.
    The exact vision model is controlled by DEEPSEEK_VISION_MODEL.
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ DeepSeek API key is not configured."
    if not DEEPSEEK_VISION_MODEL:
        return "⚠️ DeepSeek vision model is not configured."

    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})

    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    )

    payload = {
        "model": DEEPSEEK_VISION_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=90)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()
