import httpx
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

class DeepSeekError(RuntimeError):
    pass

async def generate_text(prompt: str, system: str | None = None, temperature: float = 0.7, timeout: int = 60) -> str:
    if not DEEPSEEK_API_KEY:
        raise DeepSeekError("DEEPSEEK_API_KEY не задан. Добавь его в Railway Variables.")
    prompt = (prompt or "").strip()
    if not prompt:
        return "Пустой запрос. Напиши вопрос текстом 🙂"

    messages = []
    if system:
        messages.append({"role":"system","content":system})
    messages.append({"role":"user","content":prompt})

    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/v1/chat/completions"

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise DeepSeekError(f"DeepSeek error {r.status_code}: {r.text[:400]}")
        data = r.json()
        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except Exception:
            raise DeepSeekError(f"Unexpected DeepSeek response: {str(data)[:400]}")
