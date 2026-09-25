import uuid as uuid_module

from tests.conftest import auth_headers, make_user


def test_global_theme_defaults_to_factory(client, app):
    user = make_user()
    resp = client.get("/api/v1/personalization/theme", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["is_factory_default"] is True
    assert body["bubble_color_sent"] == "#F5A623"
    assert body["bubble_shape"] == "rounded"


def test_set_and_get_global_theme(client, app):
    user = make_user()
    payload = {
        "wallpaper_type": "solid",
        "wallpaper_value": "#1F6F54",
        "bubble_color_sent": "#F5A623",
        "bubble_color_received": "#FFFBF5",
        "bubble_shape": "compact",
        "text_scale": 1.2,
        "dark_mode_brightness": 0.4,
    }
    put = client.put("/api/v1/personalization/theme", json=payload, headers=auth_headers(user))
    assert put.status_code == 200
    got = client.get("/api/v1/personalization/theme", headers=auth_headers(user)).get_json()
    assert got["wallpaper_type"] == "solid"
    assert got["bubble_shape"] == "compact"
    assert got["is_factory_default"] is False


def test_invalid_theme_rejected(client, app):
    user = make_user()
    resp = client.put("/api/v1/personalization/theme",
                      json={"wallpaper_type": "hologram", "wallpaper_value": "x"},
                      headers=auth_headers(user))
    assert resp.status_code == 422


def test_scoped_override_resolution_order(client, app):
    """override → global default → factory default (doc 3 §4 themeProvider contract)."""
    from app.models import Match

    a = make_user(display_name="A")
    b = make_user(display_name="B")
    match = Match(user_a_id=a.id, user_b_id=b.id)
    import datetime as dt

    match.matched_at = dt.datetime.now(dt.timezone.utc)
    from app.extensions import db

    db.session.add(match)
    db.session.commit()

    client.put("/api/v1/personalization/theme",
               json={"wallpaper_type": "solid", "wallpaper_value": "#7B1E3A"},
               headers=auth_headers(a))

    scoped = client.get(f"/api/v1/personalization/theme/match/{match.id}", headers=auth_headers(a))
    body = scoped.get_json()
    assert body["scope"] == "match"
    assert body["wallpaper_value"] == "#7B1E3A"

    client.put(f"/api/v1/personalization/theme/match/{match.id}",
               json={"wallpaper_type": "gradient", "wallpaper_value": "#F5A623|#7B1E3A"},
               headers=auth_headers(a))
    overridden = client.get(f"/api/v1/personalization/theme/match/{match.id}",
                            headers=auth_headers(a)).get_json()
    assert overridden["wallpaper_type"] == "gradient"

    other_match_user = make_user(display_name="C")
    forbidden = client.get(f"/api/v1/personalization/theme/match/{match.id}",
                           headers=auth_headers(other_match_user))
    assert forbidden.status_code == 404


def test_delete_scoped_reverts_to_global(client, app):
    from app.models import Match
    from app.extensions import db
    import datetime as dt

    a = make_user()
    b = make_user()
    match = Match(user_a_id=a.id, user_b_id=b.id, matched_at=dt.datetime.now(dt.timezone.utc))
    db.session.add(match)
    db.session.commit()

    url = f"/api/v1/personalization/theme/match/{match.id}"
    client.put(url, json={"wallpaper_type": "preset", "wallpaper_value": "festival_dashain"},
               headers=auth_headers(a))
    reset = client.delete(url, headers=auth_headers(a))
    assert reset.status_code == 200
    assert reset.get_json()["reset"] is True
    assert reset.get_json()["wallpaper_value"] == "brand_marigold_warm"


def test_wallpaper_upload_gated_by_moderation(client, app, monkeypatch):
    import io

    from app.services import groq_service

    user = make_user()
    data = {"image": (io.BytesIO(b"fakepngbytes"), "wall.png", "image/png")}
    resp = client.post("/api/v1/personalization/theme/upload", data=data,
                       content_type="multipart/form-data", headers=auth_headers(user))
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["moderation_status"] == "pending"
    assert body["usable"] is False

    monkeypatch.setattr(groq_service, "moderate_content",
                        lambda text: {"flagged": True, "categories": ["sexual"], "available": True})
    from app.tasks.moderation_tasks import moderate_wallpaper_upload

    result = moderate_wallpaper_upload.run(body["upload_id"])
    assert result["status"] == "rejected"


def test_presets_endpoint_lists_catalog(client, app):
    from app.models import ChatThemePreset
    from app.extensions import db

    db.session.add(ChatThemePreset(
        key="brand_marigold_warm", pack="brand", name="Marigold Warm",
        wallpaper_type="gradient", wallpaper_value="#F5A623|#C97D0C",
        bubble_color_sent="#F5A623", bubble_color_received="#FDE9C8",
    ))
    db.session.commit()
    user = make_user()
    resp = client.get("/api/v1/personalization/presets", headers=auth_headers(user))
    assert resp.status_code == 200
    presets = resp.get_json()["presets"]
    assert presets[0]["key"] == "brand_marigold_warm"
