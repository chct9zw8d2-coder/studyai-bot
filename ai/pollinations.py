import httpx
from urllib.parse import quote

BASE_IMG = "https://image.pollinations.ai/prompt"

class PollinationsError(RuntimeError):
    pass

async def generate_image_bytes(prompt: str, width: int = 1024, height: int = 1024, model: str = "flux", timeout: int = 120) -> bytes:
    prompt = (prompt or "").strip()
    if not prompt:
        raise PollinationsError("Пустой запрос для картинки.")
    q = quote(prompt)
    url = f"{BASE_IMG}/{q}"
    params = {"width": width, "height": height, "model": model}

    last_err = None
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for _ in range(2):
            try:
                r = await client.get(url, params=params)
                if r.status_code == 200 and r.content:
                    return r.content
                last_err = f"{r.status_code}: {r.text[:200]}"
            except Exception as e:
                last_err = str(e)
        raise PollinationsError(f"Ошибка генерации (Pollinations): {last_err}")
