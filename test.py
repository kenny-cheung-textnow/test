# app_after.py
import time, math, redis
from flask import Flask, request, jsonify

app = Flask(__name__)
r = redis.Redis(host="localhost", port=6379, db=0)

WINDOW = 300  # 5 min
LIMIT_IP        = 50   # attempts per IP per window
LIMIT_USER      = 15   # attempts per username per window
LIMIT_IP_USER   = 10   # attempts per (IP, user) per window

def now() -> int:
    return int(time.time())

def bump(window_key: str) -> int:
    """
    Sliding window using ZSET of timestamps.
    Returns current count after pruning the window.
    """
    t = now()
    pipe = r.pipeline()
    pipe.zadd(window_key, {str(t): t})
    pipe.zremrangebyscore(window_key, 0, t - WINDOW)
    pipe.zcard(window_key)
    pipe.expire(window_key, WINDOW)
    _, _, count, _ = pipe.execute()
    return int(count)

def limited(key: str, limit: int) -> bool:
    return bump(key) > limit

def failure_backoff_key(user: str, ip: str) -> str:
    return f"bo:{user}:{ip}"

def register_failure_and_get_delay(user: str, ip: str) -> int:
    """
    Exponential backoff per (user, ip) pair.
    Resets on success. Delay capped.
    """
    k = failure_backoff_key(user, ip)
    fails = r.incr(k)
    r.expire(k, 900)  # backoff window 15 min
    # Exponential backoff: 0,1,2,4,8,... up to 32 seconds
    return min(32, 2 ** max(0, fails - 1))

def clear_failures(user: str, ip: str):
    r.delete(failure_backoff_key(user, ip))

def check_password(user, pwd):
    # pretend DB lookup
    return user == "alice" and pwd == "correct-horse-battery-staple"

@app.post("/login")
def login():
    ip   = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    user = (request.form.get("user") or "").strip().lower()
    pwd  = (request.form.get("pwd") or "")

    # 1) Rate limits
    if limited(f"rl:ip:{ip}", LIMIT_IP):
        return jsonify({"ok": False, "error": "rate_limited_ip"}), 429
    if limited(f"rl:user:{user}", LIMIT_USER):
        return jsonify({"ok": False, "error": "rate_limited_user"}), 429
    if limited(f"rl:ipuser:{ip}:{user}", LIMIT_IP_USER):
        return jsonify({"ok": False, "error": "rate_limited_ip_user"}), 429

    # 2) Backoff on repeated failures for this (user, ip)
    delay = 0
    bo_key = failure_backoff_key(user, ip)
    fails = int(r.get(bo_key) or 0)
    if fails > 0:
        # compute current delay without incrementing yet
        delay = min(32, 2 ** max(0, fails - 1))
    if delay > 0:
        retry_after = delay
        return (
            jsonify({"ok": False, "error": "backoff", "retry_after_seconds": retry_after}),
            429,
            {"Retry-After": str(retry_after)},
        )

    # 3) Authenticate
    if check_password(user, pwd):
        clear_failures(user, ip)
        # TIP: On success, consider rotating session, enforcing MFA, etc.
        return jsonify({"ok": True})

    # 4) On failure, increment backoff and return 401 + Retry-After
    retry_after = register_failure_and_get_delay(user, ip)
    return (
        jsonify({"ok": False, "error": "invalid_credentials", "retry_after_seconds": retry_after}),
        401,
        {"Retry-After": str(retry_after)},
    )
