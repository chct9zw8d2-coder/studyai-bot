import requests
from typing import Optional
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

def generate_text(prompt: str, system: Optional[str] = None, max_tokens: int = 900) -> str:
    if not DEEPSEEK_API_KEY:
        return "⚠️ DeepSeek API key is not configured."
    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": DEEPSEEK_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()
