import requests

from config import STABILITY_API_KEY, STABILITY_ENDPOINT, STABILITY_OUTPUT_FORMAT


class StabilityError(RuntimeError):
    pass


def generate_image_bytes(prompt: str, *, aspect_ratio: str = "1:1", seed: int | None = None) -> bytes:
    """Generate an image from a text prompt using Stability AI REST API.

    This uses the Stability "Stable Image" REST endpoints which return raw image bytes.
    The endpoint may differ by account/model; configure STABILITY_ENDPOINT in env.
    """
    if not STABILITY_API_KEY or not STABILITY_ENDPOINT:
        raise StabilityError("Stability API is not configured")

    data = {
        "prompt": prompt,
        "output_format": STABILITY_OUTPUT_FORMAT or "png",
        "aspect_ratio": aspect_ratio,
    }
    if seed is not None:
        data["seed"] = str(int(seed))

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*",
    }

    resp = requests.post(
        STABILITY_ENDPOINT,
        headers=headers,
        files={"none": ("", "")},  # forces multipart/form-data
        data=data,
        timeout=180,
    )
    if resp.status_code >= 400:
        raise StabilityError(f"HTTP {resp.status_code}: {resp.text[:400]}")
    return resp.content
