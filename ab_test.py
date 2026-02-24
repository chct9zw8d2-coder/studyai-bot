import hashlib

def _bucket(user_id: int, experiment: str, buckets: int) -> int:
    key = f"{experiment}:{user_id}".encode("utf-8")
    h = hashlib.sha256(key).hexdigest()
    return int(h[:8], 16) % buckets

def choose_variant(user_id: int, experiment: str, variants: list[str]) -> str:
    if not variants:
        return "control"
    idx = _bucket(user_id, experiment, len(variants))
    return variants[idx]
