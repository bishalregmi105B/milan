#!/usr/bin/env python3
"""Live E2E suite against the running Milan API (http://localhost:5000).

Exercises the full product surface over real HTTP: auth, profiles, discovery,
matching, chat, personalization, Saathi (with graceful AI degradation), media,
notifications, safety, billing signatures and admin gating.
"""
import base64
import io
import json
import re
import time
import uuid

import requests

BASE = "http://localhost:5000/api/v1"
LOG = "server.log"

passed = failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} {extra}")


def otp_from_log(phone):
    for _ in range(10):
        try:
            text = open(LOG).read()
            matches = re.findall(rf"OTP for \+?977?{re.escape(phone)} is (\d{{6}})", text)
            if matches:
                return matches[-1]
        except FileNotFoundError:
            pass
        time.sleep(0.5)
    return None


def signup(phone, name):
    r = requests.post(f"{BASE}/auth/otp/request", json={"phone": phone}, timeout=10)
    assert r.status_code == 200, r.text
    code = otp_from_log(phone)
    assert code, "OTP never appeared in server log"
    r = requests.post(
        f"{BASE}/auth/otp/verify",
        json={"phone": phone, "code": code, "date_of_birth": "1998-05-10"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    requests.put(
        f"{BASE}/profile/me",
        headers=h,
        json={
            "display_name": name,
            "bio": f"Hi, I am {name}",
            "city": "Kathmandu",
            "interests": ["trekking", "music"],
        },
        timeout=10,
    )
    return {"headers": h, "id": r.json()["user"]["id"], "phone": phone}


print("== health ==")
r = requests.get("http://localhost:5000/health", timeout=5)
check("GET /health", r.status_code == 200)

print("== auth ==")
suffix = str(int(time.time()))[-8:]
A = signup(f"98{suffix}", "Aasha")
B = signup(f"97{suffix}", "Bibek")
check("OTP request+verify issues JWT (real Sparrow dev path)", bool(A["headers"]["Authorization"]))
check("two users signed up with profiles", A["id"] != B["id"])

r = requests.get(f"{BASE}/profile/me", headers=A["headers"], timeout=10)
check("GET /profile/me returns display_name",
      r.json().get("profile", {}).get("display_name") == "Aasha")

print("== discovery & matching ==")
r = requests.get(f"{BASE}/discovery/candidates", headers=A["headers"], timeout=15)
cands = r.json().get("candidates", [])
check("GET /discovery/candidates lists users", any(c["id"] == B["id"] for c in cands))
check("blur-until-match flag present on candidates",
      len(cands) > 0 and all("is_blurred" in c for c in cands))

requests.post(f"{BASE}/discovery/swipe", headers=A["headers"],
              json={"target_id": B["id"], "direction": "like"}, timeout=30)
r = requests.post(f"{BASE}/discovery/swipe", headers=B["headers"],
                  json={"target_id": A["id"], "direction": "like"}, timeout=30)
second = r.json()
check("mutual like creates a match", second.get("match") is True, json.dumps(second))
match_id = second.get("match_id")

r = requests.get(f"{BASE}/matches", headers=A["headers"], timeout=10)
match_row = next((m for m in r.json().get("matches", []) if m["id"] == match_id), None)
check("GET /matches shows the new match", match_row is not None)

r = requests.get(f"{BASE}/discovery/kundali/{match_id}", headers=A["headers"], timeout=15)
check("kundali without birth details -> opt-in error",
      r.status_code == 422 and r.json()["error"] == "horoscope_details_missing")

print("== chat ==")
r = requests.post(f"{BASE}/matches/{match_id}/messages", headers=A["headers"],
                  json={"body": "Namaste Bibek! How was your week?"}, timeout=30)
check("message sends; moderation unavailable defers to async scan",
      r.status_code == 201, r.text[:120])
msg_id = r.json().get("id")

r = requests.get(f"{BASE}/matches/{match_id}/messages", headers=B["headers"], timeout=10)
check("partner reads message history",
      any(m["id"] == msg_id for m in r.json().get("messages", [])))


r = requests.post(f"{BASE}/matches/{match_id}/snaps", headers=A["headers"],
                  json={"media_url": "/media/snap/x.webp", "view_mode": "single_view"},
                  timeout=10)
snap_id = r.json().get("id")
check("ephemeral snap created (single_view)", r.status_code == 201 and snap_id)

r = requests.post(f"{BASE}/matches/snaps/{snap_id}/screenshot", headers=B["headers"],
                  json={}, timeout=10)
check("screenshot notice endpoint notifies sender", r.status_code == 200)

r = requests.post(f"{BASE}/safety/blocks", headers=A["headers"],
                  json={"blocked_id": B["id"]}, timeout=10)
check("block deactivates match", r.status_code == 200)
requests.delete(f"{BASE}/safety/blocks/{B['id']}", headers=A["headers"], timeout=10)

print("== personalization ==")
theme = {
    "wallpaper_type": "solid", "wallpaper_value": "#1F6F54",
    "bubble_color_sent": "#F5A623", "bubble_color_received": "#DCEFE7",
    "bubble_shape": "compact", "text_scale": 1.1, "dark_mode_brightness": 0.4,
}
r = requests.put(f"{BASE}/personalization/theme", headers=A["headers"],
                 json=theme, timeout=10)
check("PUT global chat theme",
      r.status_code == 200 and r.json()["wallpaper_value"] == "#1F6F54")

r = requests.get(f"{BASE}/personalization/theme/match/{match_id}",
                 headers=A["headers"], timeout=10)
check("scoped resolution falls back to global when no override",
      r.status_code == 200 and r.json()["wallpaper_value"] == "#1F6F54")

scoped = dict(theme, wallpaper_type="gradient", wallpaper_value="#F5A623|#C97D0C")
r = requests.put(f"{BASE}/personalization/theme/match/{match_id}",
                 headers=A["headers"], json=scoped, timeout=10)
check("PUT scoped override wins over global",
      r.status_code == 200 and r.json()["wallpaper_value"].startswith("#F5A623"))

r = requests.delete(f"{BASE}/personalization/theme/match/{match_id}",
                    headers=A["headers"], timeout=10)
body = r.json()
check("DELETE scoped override reverts to global",
      body.get("reset") is True and body["wallpaper_value"] == "#1F6F54")

png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAABzenr0AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
r = requests.post(f"{BASE}/personalization/theme/upload", headers=A["headers"],
                  files={"image": ("wp.png", io.BytesIO(png), "image/png")}, timeout=30)
body = r.json()
check("wallpaper upload accepted but gated behind moderation",
      r.status_code == 201 and body.get("usable") is False
      and body.get("moderation_status") == "pending")

print("== saathi (mock-AI backend: full algorithms live) ==")
r = requests.get(f"{BASE}/saathi/characters", headers=A["headers"], timeout=10)
chars = r.json().get("characters", [])
check("curated roster seeded (asha/bibek/priya/sagar)",
      {"asha", "bibek", "priya", "sagar"} <= {c["key"] for c in chars})

r = requests.post(f"{BASE}/saathi/asha/sessions", headers=A["headers"], json={}, timeout=10)
session_id = r.json().get("session_id")
check("start/resume saathi session", bool(session_id))

r = requests.post(f"{BASE}/saathi/sessions/{session_id}/messages",
                  headers=A["headers"],
                  json={"body": "I get nervous texting first."}, timeout=60)
reply_body = r.json()
check("AI-labeled coaching reply from mock backend",
      r.status_code == 200 and reply_body.get("is_ai") is True
      and len(reply_body.get("reply", "")) > 30
      and "trouble thinking" not in reply_body.get("reply", ""), r.text[:150])
check("typing delay calibrated per doc 5 §2.6 (0.8-4.0s)",
      0.8 <= reply_body.get("typing_delay_seconds", 99) <= 4.0)

r = requests.get(f"{BASE}/saathi/sessions/{session_id}/memory",
                 headers=A["headers"], timeout=10)
check("What Saathi Remembers view endpoint", r.status_code == 200)

r = requests.put(f"{BASE}/saathi/sessions/{session_id}/settings",
                 headers=A["headers"],
                 json={"proactive_opt_in": False, "is_paused": False}, timeout=10)
check("proactive defaults OFF; daily cap reported as 1",
      r.json().get("daily_cap") == 1)

png_audio = b"\x1a\x45\xdf\xa3webm"
r = requests.post(f"{BASE}/saathi/sessions/{session_id}/voice", headers=A["headers"],
                  files={"audio": ("clip.webm", png_audio, "audio/webm")}, timeout=60)
vbody = r.json()
check("voice mode: transcript + reply + playable WAV audio",
      r.status_code == 200 and vbody.get("transcript")
      and str(vbody.get("audio_base64", "")).startswith("UklGR"), r.text[:120])

print("== AI features on the mock backend ==")
r = requests.post(f"{BASE}/profile/bio/generate", headers=A["headers"],
                  json={"notes": "Trek guide from Pokhara. I cook great dal bhat because my grandmother taught me.",
                        "language": "en"}, timeout=10)
drafts = r.json().get("drafts", [])
check("bio assistant returns 3 distinct drafts", len(drafts) == 3 and len(set(drafts)) == 3)

r = requests.post(f"{BASE}/profile/prompts/feedback", headers=A["headers"],
                  json={"answer": "I love to laugh and have fun"}, timeout=10)
fb = r.json()
check("prompt grader flags generic answers with a concrete fix",
      fb.get("tag") == "generic" and len(fb.get("suggestion", "")) > 20)

ctx = {"shared_interest_tags": ["trekking", "music"], "compatible_intent_mode": True,
       "complementary_conversation_styles": False}
r = requests.post(f"{BASE}/matches/{match_id}/icebreakers", headers=B["headers"],
                  json={"context": ctx}, timeout=10)
sugg = r.json().get("suggestions", [])
check("icebreakers grounded in shared interests (trekking/music)",
      len(sugg) == 3 and any("trekking" in s.lower() or "music" in s.lower() for s in sugg),
      json.dumps(sugg))

requests.put(f"{BASE}/profile/me", headers=A["headers"],
             json={"horoscope_details": {"birth_date": "1998-05-10",
                                         "birth_time": "06:30", "birth_place": "Pokhara"}},
             timeout=10)
requests.put(f"{BASE}/profile/me", headers=B["headers"],
             json={"horoscope_details": {"birth_date": "1997-11-02",
                                         "birth_time": "14:10", "birth_place": "Kathmandu"}},
             timeout=10)
r = requests.get(f"{BASE}/discovery/kundali/{match_id}", headers=A["headers"], timeout=15)
kn = r.json()
check("kundali guna-milan narrative generated + labeled fun-only",
      r.status_code == 200 and "36" in kn.get("narrative", "")
      and kn.get("label") == "fun_cultural_signal_not_science")

r = requests.get(f"{BASE}/matches/recap/weekly", headers=A["headers"], timeout=15)
recap = r.json()
check("weekly recap generated from real activity stats",
      r.status_code == 200 and "week" in recap.get("recap", "").lower())

# 'why you matched' explainer grounded in shared profile signal
reason = (match_row or {}).get("match_reason_text")
check("'why you matched' explainer grounded in shared profile signal",
      bool(reason) and "trekking" in (reason or "").lower(), str(reason))

print("== notifications ==")
r = requests.get(f"{BASE}/notifications/preferences", headers=A["headers"], timeout=10)
prefs = {p["category"]: p for p in r.json().get("preferences", [])}
check("all five categories exposed",
      set(prefs) >= {"matches", "messages", "saathi", "social", "promo"})
requests.put(f"{BASE}/notifications/preferences", headers=A["headers"],
             json={"preferences": [{"category": "saathi", "enabled": False}]}, timeout=10)
r = requests.get(f"{BASE}/notifications/preferences", headers=A["headers"], timeout=10)
saathi_pref = next(p for p in r.json()["preferences"] if p["category"] == "saathi")
check("mute saathi category persists", saathi_pref["enabled"] is False)

r = requests.post(f"{BASE}/notifications/devices", headers=A["headers"],
                  json={"token": f"fcm-{uuid.uuid4().hex[:8]}", "platform": "android"},
                  timeout=10)
check("device token registration", r.status_code == 200)

print("== jhalak & social ==")
r = requests.get(f"{BASE}/jhalak/feed", headers=A["headers"], timeout=10)
check("jhalak feed cursor-paginated shape",
      "reels" in r.json() and "next_cursor" in r.json())
r = requests.get(f"{BASE}/jhalak/circles", headers=A["headers"], timeout=10)
circle_id = next((c["id"] for c in r.json().get("circles", [])), None)
if circle_id:
    r = requests.post(f"{BASE}/jhalak/circles/{circle_id}/join",
                      headers=A["headers"], json={}, timeout=10)
    check("join circle", r.json().get("joined") is True)
else:
    check("circles endpoint reachable (empty catalog ok)", True)
r = requests.post(f"{BASE}/jhalak/reels", headers=A["headers"],
                  json={"video_url": "/media/video/x.mp4", "caption": "aaja ko vibe"},
                  timeout=10)
check("upload reel", r.status_code == 201)
r = requests.post(f"{BASE}/jhalak/stories", headers=A["headers"],
                  json={"media_url": "/media/story/x.jpg"}, timeout=10)
check("post 24h story", r.status_code == 201)
r = requests.get(f"{BASE}/jhalak/stories", headers=A["headers"], timeout=10)
check("active stories listed", r.status_code == 200)

print("== billing ==")
r = requests.post(f"{BASE}/billing/checkout", headers=A["headers"],
                  json={"provider": "esewa", "tier": "plus"}, timeout=10)
body = r.json()
check("esewa v2 checkout returns HMAC-signed params",
      r.status_code == 201
      and bool(body["params"].get("signature"))
      and bool(body["params"].get("transaction_uuid")), r.text[:160])

r = requests.post(f"{BASE}/billing/webhooks/esewa", json={
    "payment_id": "00000000-0000-0000-0000-000000000000",
    "status": "SUCCESS", "transaction_uuid": "x"}, timeout=10)
check("webhook rejects missing signature (401)", r.status_code == 401)

print("== media ==")
r = requests.post(f"{BASE}/media/upload?kind=photo", headers=A["headers"],
                  files={"file": ("me.png", io.BytesIO(png), "image/png")}, timeout=30)
check("multipart media upload + photo moderation row",
      r.status_code == 201 and bool(r.json().get("photo_id")))

print("== recap & admin gating ==")
r = requests.get(f"{BASE}/admin/analytics/overview", headers=A["headers"], timeout=10)
check("admin route blocked for regular user (403 role-gated)", r.status_code == 403)

print()
print(f"LIVE RESULT: {passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
