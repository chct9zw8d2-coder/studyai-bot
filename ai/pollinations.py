import json, time, urllib.parse, requests

def _maybe_extract_content(text: str) -> str:
    s = text.strip()
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                if isinstance(obj.get("content"), str) and obj["content"].strip():
                    return obj["content"].strip()
        except Exception:
            pass
    return text

def generate_image_bytes(prompt: str, width: int = 1024, height: int = 1024, retries: int = 3) -> bytes:
    q = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{q}?width={width}&height={height}&model=flux"
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code >= 500:
                raise RuntimeError(f"Server error {r.status_code}")
            r.raise_for_status()
            return r.content
        except Exception as e:
            last = e
            time.sleep(1.5*(i+1))
    raise last
