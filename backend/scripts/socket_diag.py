"""Milan socket diagnostic — proves or disproves each link in the live-chat
chain with real clients, printing exactly which step fails.

Run on the server:
    cd /var/www/milan/backend && set -a && . ./.env && set +a \
      && venv/bin/python socket_diag.py [--remote]

Steps checked:
  1. engine.io handshake (polling + websocket transports)
  2. socket.io CONNECT with a valid JWT (auth handshake)
  3. chat:join ack for a real match
  4. two clients in one room: A sends REST message -> B receives chat:message
  5. typing relay: A emits chat:typing_start -> B receives chat:typing
  6. companion path: user message -> broadcast typing -> reply arrives
  7. push row: notification queued for the recipient
"""
import argparse
import sys
import time

import requests
import socketio

BASE_LOCAL = "http://127.0.0.1:5003"
BASE_REMOTE = "https://milanapi.pukarphulara.com.np"


def log(step, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {step}" + (f" — {detail}" if detail else ""), flush=True)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    base = BASE_REMOTE if args.remote else BASE_LOCAL
    api = f"{base}/api/v1"
    print(f"=== target: {base} ===")

    from app import create_app
    from app.extensions import db

    app = create_app("prod")
    with app.app_context():
        from flask_jwt_extended import create_access_token

        from app.models import Match, Message, Notification, User

        # ── fixtures: two real human users with an active match ───────────
        users = User.query.filter_by(is_ai=False).limit(2).all()
        if len(users) < 2:
            return 1 if not log("fixtures", False, "need 2 human users") else 1
        a, b = users[0], users[1]
        match = Match.query.filter(
            Match.is_active.is_(True),
            ((Match.user_a_id == a.id) & (Match.user_b_id == b.id))
            | ((Match.user_a_id == b.id) & (Match.user_b_id == a.id)),
        ).first()
        created_match = False
        if match is None:
            from datetime import datetime, timezone

            match = Match(user_a_id=a.id, user_b_id=b.id,
                          matched_at=datetime.now(timezone.utc), kind="human")
            db.session.add(match)
            db.session.commit()
            created_match = True
        with app.test_request_context():
            token_a = create_access_token(identity=str(a.id))
            token_b = create_access_token(identity=str(b.id))
        match_id = str(match.id)
        log("fixtures", True, f"A={str(a.id)[:8]} B={str(b.id)[:8]} match={match_id[:8]}"
            + (" (created)" if created_match else ""))

    # ── 1. engine.io handshake per transport ─────────────────────────────
    for transport in ("polling", "websocket"):
        try:
            r = requests.get(f"{base}/socket.io/",
                             params={"EIO": 4, "transport": transport},
                             timeout=8)
            log(f"eio handshake [{transport}]", r.status_code == 200,
                f"HTTP {r.status_code}")
        except Exception as exc:
            log(f"eio handshake [{transport}]", False, str(exc)[:70])

    # ── 2/3/4/5. two live clients ────────────────────────────────────────
    received_b = []
    typing_b = []

    client_a = socketio.Client(reconnection=False)
    client_b = socketio.Client(reconnection=False)

    @client_b.on("chat:message")
    def _on_msg(data):
        received_b.append(data)

    @client_b.on("chat:typing")
    def _on_typing(data):
        typing_b.append(data)

    transport_used = None
    for transports in (["websocket"], ["polling"]):
        try:
            client_a.connect(base, transports=transports, auth={"token": token_a})
            client_b.connect(base, transports=transports, auth={"token": token_b})
            transport_used = client_a.transport()
            break
        except Exception as exc:
            log(f"socket connect {transports}", False, str(exc)[:70])
            for c in (client_a, client_b):
                try:
                    c.disconnect()
                except Exception:
                    pass
    if transport_used is None:
        return 1
    log("socket connect (both clients)", True, f"transport={transport_used}")

    ack_a = client_a.call("chat:join", {"match_id": match_id}, timeout=8)
    ack_b = client_b.call("chat:join", {"match_id": match_id}, timeout=8)
    log("chat:join ack", bool(ack_a and ack_a.get("ok")) and bool(ack_b and ack_b.get("ok")),
        f"A={ack_a} B={ack_b}")

    # typing relay A -> B
    typing_b.clear()
    client_a.emit("chat:typing_start", {"match_id": match_id})
    time.sleep(2.0)
    log("typing relay A→B", any(t.get("typing") for t in typing_b),
        f"received={typing_b}")

    # REST message from A -> socket delivery to B
    received_b.clear()
    body = f"diag ping {int(time.time())}"
    resp = requests.post(f"{api}/matches/{match_id}/messages",
                         headers={"Authorization": f"Bearer {token_a}"},
                         json={"body": body}, timeout=20)
    log("REST send (A)", resp.status_code == 201, f"HTTP {resp.status_code}")
    deadline = time.time() + 10
    while time.time() < deadline and not received_b:
        time.sleep(0.4)
    got = any(m.get("body") == body for m in received_b)
    log("socket delivery A→B", got,
        f"received={[m.get('body') for m in received_b]}")

    # ── 7. push row queued for B ─────────────────────────────────────────
    with app.app_context():
        from app.models import Notification

        note = (Notification.query.filter_by(user_id=b.id, category="messages")
                .order_by(Notification.created_at.desc()).first())
        fresh = note is not None and (time.time() - note.created_at.timestamp()) < 120
        log("push row queued for B", fresh,
            f"latest={note.title if note else None}")

    for c in (client_a, client_b):
        try:
            c.disconnect()
        except Exception:
            pass

    # ── 6. companion path ────────────────────────────────────────────────
    with app.app_context():
        from app.models import SaathiSession

        session = SaathiSession.query.filter_by(user_id=a.id).first()
    if session is None:
        started = requests.post(f"{api}/saathi/aarohi/sessions",
                                headers={"Authorization": f"Bearer {token_a}"},
                                timeout=20)
        companion_match = started.json().get("match_id") if started.ok else None
    else:
        companion_match = str(session.match_id) if session.match_id else None
    if not companion_match:
        log("companion fixtures", False, "no companion match")
        return 1

    ai_typing = []
    ai_msgs = []
    client_ai = socketio.Client(reconnection=False)

    @client_ai.on("chat:typing")
    def _ai_typing(data):
        ai_typing.append((time.time(), data))

    my_id = None

    @client_ai.on("chat:message")
    def _ai_msg(data):
        # the user's own echo also lands here — only HER messages count
        if my_id and str(data.get("sender_id")) == my_id:
            return
        ai_msgs.append((time.time(), data))

    my_id = str(a.id)
    client_ai.connect(base, transports=["polling"], auth={"token": token_a})
    ack = client_ai.call("chat:join", {"match_id": companion_match}, timeout=8)
    log("companion chat:join", bool(ack and ack.get("ok")), str(ack))

    t_send = time.time()
    r = requests.post(f"{api}/matches/{companion_match}/messages",
                      headers={"Authorization": f"Bearer {token_a}"},
                      json={"body": "diag: timi k garchau aaja?"}, timeout=20)
    log("companion REST send", r.status_code == 201,
        f"pending={r.json().get('companion_pending') if r.ok else r.status_code}")

    # typing must arrive EARLY (before generation finishes)
    deadline = time.time() + 75
    while time.time() < deadline and not ai_msgs:
        time.sleep(0.5)
    first_typing = (ai_typing[0][0] - t_send) if ai_typing else None
    reply_at = (ai_msgs[0][0] - t_send) if ai_msgs else None
    log("companion typing broadcast", first_typing is not None,
        f"+{first_typing:.1f}s" if first_typing else "never")
    log("companion reply delivered", bool(ai_msgs),
        f"+{reply_at:.1f}s body={ai_msgs[0][1].get('body')[:40] if ai_msgs else ''}")
    if first_typing is not None and reply_at is not None:
        log("typing precedes reply", first_typing < reply_at - 1,
            f"typing +{first_typing:.1f}s vs reply +{reply_at:.1f}s")

    try:
        client_ai.disconnect()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
