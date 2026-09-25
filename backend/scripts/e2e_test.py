"""End-to-end test of the deployed Milan API (run ON the VPS).

    cd /var/www/milan/backend && ./venv/bin/python scripts/e2e_test.py
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/var/www/milan/backend")

API = "https://milanapi.pukarphulara.com.np/api/v1"
REDIS_DB = 3

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name} {detail}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def req(method: str, path: str, body=None, token=None, retries: int = 5):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    for attempt in range(retries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Content-Type", "application/json")
        r.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) MilanE2E/1.0")
        if token:
            r.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode() or "{}"
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                if e.code == 429 and attempt < retries - 1:
                    import time as _t
                    _t.sleep(6)
                    continue
                return e.code, {"raw": raw[:200]}
        except Exception as exc:  # noqa: BLE001
            if attempt < retries - 1:
                import time as _t
                _t.sleep(3)
                continue
            return 0, {"raw": str(exc)}
    return 0, {}


def get_otp(email: str) -> str:
    import subprocess
    out = subprocess.run(
        ["redis-cli", "-n", str(REDIS_DB), "--scan", "--pattern", f"otp:*{email}"],
        capture_output=True, text=True,
    ).stdout.strip().splitlines()
    if not out:
        return ""
    return subprocess.run(
        ["redis-cli", "-n", str(REDIS_DB), "get", out[0]],
        capture_output=True, text=True,
    ).stdout.strip().strip('"')


def login(email: str) -> str:
    status, body = req("POST", "/auth/otp/request", {"email": email})
    assert status == 200, f"otp request failed: {body}"
    code = get_otp(email)
    assert code, "no otp in redis"
    status, body = req("POST", "/auth/otp/verify", {"email": email, "code": code})
    assert status == 200, f"verify failed: {body}"
    return body["access_token"]


def user_id_by_email(email: str) -> str:
    import subprocess
    out = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", "milan", "-t", "-A", "-c",
         f"SELECT id FROM users WHERE email='{email}'"],
        capture_output=True, text=True,
    )
    return out.stdout.strip()


def main():
    print("== 1. AUTH FLOW ==")
    t1 = login("aarati.demo@milanapp.live")
    check("email OTP login", bool(t1))
    t2 = login("bibek.demo@milanapp.live")
    check("second user login", bool(t2))

    print("== 2. PROFILE ==")
    status, me = req("GET", "/profile/me", token=t1)
    check("GET /profile/me", status == 200, f"({me.get('profile', {}).get('display_name', '?')})")

    print("== 3. DISCOVERY ==")
    status, deck = req("GET", "/discovery/candidates", token=t1)
    check("GET /discovery/candidates", status == 200 and len(deck.get("candidates", [])) > 0,
          f"({len(deck.get('candidates', []))} candidates)")

    print("== 4. SWIPE + MATCH ==")
    bibek = user_id_by_email("bibek.demo@milanapp.live")
    status, r = req("POST", "/discovery/swipe", {"target_id": bibek, "direction": "like"}, token=t1)
    check("Aarati likes Bibek", status == 200, f"({r})")
    aarati = user_id_by_email("aarati.demo@milanapp.live")
    status, r = req("POST", "/discovery/swipe", {"target_id": aarati, "direction": "like"}, token=t2)
    check("Bibek likes Aarati (mutual match)", status == 200, f"(matched={r.get('matched', r.get('match'))})")

    print("== 5. CHAT ==")
    status, matches = req("GET", "/matches", token=t1)
    check("list matches", status == 200, f"({status})")
    match_id = None
    if status == 200 and matches:
        items = matches if isinstance(matches, list) else matches.get("matches", [])
        if items:
            match_id = items[0].get("id")
    if match_id:
        status, r = req("POST", f"/matches/{match_id}/messages", {"body": "Hi Bibek! Nepal tourism week soon - hiking?"}, token=t1)
        check("send chat message", status in (200, 201), f"({status} {str(r)[:80]})")
        status, r = req("GET", f"/matches/{match_id}/messages", token=t2)
        check("receive messages", status == 200 and len(r.get("messages", [])) >= 1)
    else:
        check("match id found", False, "no matches list")

    print("== 6. SAATHI AI (Groq) ==")
    status, chars = req("GET", "/saathi/characters", token=t1)
    check("GET /saathi/characters", status == 200 and len(chars.get("characters", chars if isinstance(chars, list) else [])) >= 4)
    char_list = chars.get("characters", chars) if isinstance(chars, (dict, list)) else []
    char_id = None
    if isinstance(char_list, list) and char_list:
        char_id = char_list[0].get("id")
    if char_id:
        status, sess = req("POST", f"/saathi/{char_id}/sessions", token=t1)
        check("create saathi session", status in (200, 201), f"({status})")
        session_id = sess.get("session", sess).get("id") if isinstance(sess, dict) else None
        if session_id:
            status, reply = req("POST", f"/saathi/sessions/{session_id}/messages",
                                {"content": "Hey! I have a date tomorrow and I'm nervous. Any tips?"}, token=t1)
            body = reply.get("reply", reply.get("message", ""))
            check("saathi AI reply (Groq)", status == 200 and len(str(body)) > 20, f"({str(body)[:80]})")
            status, msgs = req("GET", f"/saathi/sessions/{session_id}/messages", token=t1)
            check("saathi history", status == 200)
    else:
        check("saathi character id", False)

    print("== 7. NOTIFICATIONS ==")
    status, prefs = req("GET", "/notifications/preferences", token=t1)
    check("notification preferences", status == 200)

    print("== 8. BILLING ==")
    status, plans = req("GET", "/billing/plans")
    check("billing plans public", status == 200 and len(plans.get("tiers", [])) == 3)

    print(f"\n===== RESULTS: {PASS} passed, {FAIL} failed =====")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
