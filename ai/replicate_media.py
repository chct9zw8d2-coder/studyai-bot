
import os
import replicate

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

def _ensure():
    if not REPLICATE_API_TOKEN:
        raise RuntimeError("REPLICATE_API_TOKEN not set")
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

FLUX_MODEL = os.getenv("REPLICATE_IMAGE_MODEL", "black-forest-labs/flux-schnell")
IMG2IMG_MODEL = os.getenv("REPLICATE_IMG2IMG_MODEL", "stability-ai/stable-diffusion-img2img")
MUSIC_MODEL = os.getenv("REPLICATE_MUSIC_MODEL", "meta/musicgen")

def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    _ensure()
    r = replicate.run(
        FLUX_MODEL,
        input={"prompt": prompt, "aspect_ratio": aspect_ratio, "output_format": "jpg", "output_quality": 90, "num_outputs": 1},
    )
    if isinstance(r, list) and r:
        return r[0]
    return str(r)

def edit_image(image_url: str, prompt: str, strength: float = 0.6) -> str:
    _ensure()
    r = replicate.run(
        IMG2IMG_MODEL,
        input={"image": image_url, "prompt": prompt, "strength": strength},
    )
    if isinstance(r, list) and r:
        return r[0]
    return str(r)

def generate_music(prompt: str, duration: int = 12) -> str:
    _ensure()
    r = replicate.run(
        MUSIC_MODEL,
        input={"prompt": prompt, "duration": duration},
    )
    if isinstance(r, str):
        return r
    if isinstance(r, list) and r:
        return r[0]
    return str(r)
