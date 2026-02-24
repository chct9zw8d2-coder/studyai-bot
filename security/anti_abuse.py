import time
import hashlib
from collections import defaultdict, deque
from config import (
    RATE_LIMIT_TEXT_PER_MIN, RATE_LIMIT_IMAGE_PER_MIN,
    MAX_TEXT_LEN, DUPLICATE_WINDOW_SEC, DUPLICATE_MAX
)

_hits = defaultdict(lambda: deque())          # key: (user_id, kind)
_recent = defaultdict(lambda: deque())        # key: user_id -> deque[(ts, hash)]

def check_rate_limit(user_id: int, kind: str = "text") -> bool:
    """Simple per-user per-minute rate limit."""
    now = time.time()
    key = (user_id, kind)
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()

    limit = RATE_LIMIT_TEXT_PER_MIN if kind == "text" else RATE_LIMIT_IMAGE_PER_MIN
    if len(q) >= limit:
        return False
    q.append(now)
    return True

def is_duplicate_burst(user_id: int, text: str) -> bool:
    """Blocks repeated identical prompts in a short window."""
    now = time.time()
    h = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    q = _recent[user_id]
    while q and now - q[0][0] > DUPLICATE_WINDOW_SEC:
        q.popleft()
    # count duplicates
    dup = sum(1 for _, hh in q if hh == h)
    q.append((now, h))
    return dup >= DUPLICATE_MAX

def clamp_text(text: str) -> str:
    return text if len(text) <= MAX_TEXT_LEN else text[:MAX_TEXT_LEN]
