"""Live validation of the deployed companion stack (run on the VPS).

Validates: email OTP login -> companion roster w/ tier locks -> romantic
session -> real Groq reply + bond DTO -> in-chat proactive message task ->
ambient status post task -> socket.io handshake.
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/var/www/milan/backend")

BASE = "https://milanapi.pukarphulara.com.np/api/v1"


def api(path, method="GET", body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    # Cloudflare blocks the default Python-urllib UA (error 1010)
    req.add_header("User-Agent", "Milan-Validation/1.0 (scripts/validate_live.py)")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw or "{}")
        except json.JSONDecodeError:
            return exc.code, {"_raw": raw[:300]}


def get_otp_from_redis(email):
    import redis

    # OTP store db follows CELERY_BROKER_URL's db (3 in prod) — from_url's
    # URL db wins over the db kwarg on this redis-py version.
    for db in (3, 5):
        client = redis.Redis.from_url(f"redis://localhost:6379/{db}", socket_connect_timeout=5)
        for key in client.scan_iter(f"otp:*{email}*"):
            return client.get(key).decode()
    return None


def main() -> int:
    results = []

    # 1. Email OTP login for a seeded premium demo user
    email = "aarati.demo@milanapp.live"
    status, body = api("/auth/otp/request", "POST", {"email": email})
    results.append(("otp_request", status == 200, status))
    code = get_otp_from_redis(email)
    results.append(("otp_in_redis", bool(code), bool(code)))

    status, body = api("/auth/otp/verify", "POST",
                       {"email": email, "code": code, "date_of_birth": "1998-04-12"})
    ok = status == 200 and "access_token" in body
    results.append(("otp_verify_login", ok, status))
    token = body.get("access_token")

    # 2. Companion roster: romantic characters present + tier state
    status, body = api("/saathi/characters", token=token)
    roster = {c["key"]: c for c in body.get("characters", [])}
    has_romantics = "aarohi" in roster and "nishan" in roster
    results.append(("roster_romantics_present", has_romantics, sorted(roster)))
    results.append(("premium_unlocks_aarohi", roster.get("aarohi", {}).get("locked") is False,
                    roster.get("aarohi", {}).get("locked")))
    results.append(("roster_tier", body.get("tier") == "premium", body.get("tier")))

    # 3. Romantic companion session + REAL Groq reply
    aarohi_id = roster["aarohi"]["id"]
    status, body = api(f"/saathi/{aarohi_id}/sessions", "POST", token=token)
    sid = body.get("session_id")
    ok = status == 200 and body.get("companion_mode") == "romantic"
    results.append(("romantic_session", ok, (status, body.get("companion_mode"))))
    results.append(("bond_dto", body.get("bond", {}).get("stage") is not None, body.get("bond")))
    results.append(("presence_dto", body.get("presence", {}).get("state") is not None, body.get("presence")))

    status, body = api(f"/saathi/sessions/{sid}/messages", "POST",
                       {"body": "namaste! k cha? aaj kal kasto din bitirahechau?"}, token=token)
    reply = body.get("reply", "")
    ok = status == 200 and len(reply) > 10 and body.get("is_ai") is True
    results.append(("real_ai_reply", ok, reply[:90]))
    results.append(("timing_3stage", "read_delay_seconds" in body and "typing_delay_seconds" in body,
                    {k: body.get(k) for k in ("read_delay_seconds", "typing_delay_seconds", "segments")}))
    results.append(("bond_progress", body.get("bond", {}).get("streak_days", 0) >= 1, body.get("bond")))

    # 4. In-chat proactive message (task runs inline inside an app context —
    # the Celery ContextTask wrapper only binds contexts under the real worker)
    from app import create_app as _create_app
    from app.tasks.notification_tasks import saathi_proactive_check, saathi_status_posts
    _app = _create_app("prod")
    with _app.app_context():
        proactive = saathi_proactive_check.run()
    results.append(("proactive_task_ran", isinstance(proactive, dict), proactive))
    status, body = api(f"/saathi/sessions/{sid}/messages", token=token)
    types = {m["message_type"] for m in body.get("messages", [])}
    results.append(("proactive_in_chat", "proactive" in types, sorted(types)))

    with _app.app_context():
        status_posts = saathi_status_posts.run()
    status, body = api(f"/saathi/sessions/{sid}/status", token=token)
    results.append(("status_posts", len(body.get("posts", [])) >= 1, (status_posts, len(body.get("posts", [])))))

    # 5. Regenerate (swipe) endpoint honors tiers
    status, body = api(f"/saathi/sessions/{sid}/messages", "POST",
                       {"body": "ok tell me about your day", "regenerate_variant": 3}, token=token)
    results.append(("regenerate_premium_ok", status == 200, status))

    # 6. Socket.io handshake
    req = urllib.request.Request(
        "https://milanapi.pukarphulara.com.np/socket.io/?EIO=4&transport=polling",
        headers={"User-Agent": "Milan-Validation/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = resp.read().decode()[:40]
        results.append(("socket_io_handshake", payload.startswith("0{"), payload[:30]))
    except Exception as exc:
        results.append(("socket_io_handshake", False, repr(exc)[:80]))

    print("\n=== LIVE VALIDATION ===")
    failures = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"[{mark}] {name}: {str(detail)[:120]}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
