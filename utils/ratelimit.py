import threading
import time
from functools import wraps

from flask import abort, current_app, request

_lock = threading.Lock()
_buckets = {}

WINDOW_SECONDS = 60


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def rate_limit(scope, default_per_minute):
    """Basic in-process sliding-window limiter keyed by (scope, IP).

    The limit is read from config at request time so it is test/tunable
    per deployment: RATE_LIMIT_<SCOPE_UPPER> (per 60s).
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cfg = current_app.config
            if not cfg.get("RATE_LIMIT_ENABLED", True):
                return fn(*args, **kwargs)

            limit = int(cfg.get(f"RATE_LIMIT_{scope.upper()}", default_per_minute))
            key = (scope, _client_ip())
            now = time.time()

            with _lock:
                hits = _buckets.setdefault(key, [])
                hits[:] = [t for t in hits if t > now - WINDOW_SECONDS]
                if len(hits) >= limit:
                    abort(429, "Too many requests. Please slow down.")
                hits.append(now)

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def reset_ratelimit():
    """Clear all buckets (used between tests and in dev)."""
    with _lock:
        _buckets.clear()