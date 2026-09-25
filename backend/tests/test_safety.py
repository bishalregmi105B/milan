import uuid

from app.extensions import db
from app.models import Report
from tests.conftest import auth_headers, make_user


def test_report_uses_resolved_user_target(client):
    reporter = make_user("Reporter")
    target = make_user("Target")
    response = client.post(
        "/api/v1/safety/reports",
        json={
            "target_id": str(target.id),
            "reason": "harassment",
            "details": "Repeated unwanted messages",
        },
        headers=auth_headers(reporter),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "open"
    report = db.session.get(Report, uuid.UUID(body["id"]))
    assert report is not None
    assert str(report.target_id) == str(target.id)
    assert report.reason == "harassment"


def test_report_rejects_match_or_general_target_without_500(client):
    reporter = make_user("Reporter")
    response = client.post(
        "/api/v1/safety/reports",
        json={"target_id": "not-a-user-id", "reason": "harassment"},
        headers=auth_headers(reporter),
    )

    assert response.status_code == 422
    assert response.get_json()["error"] == "invalid_target_id"


def test_report_rejects_invalid_type_and_reference(client):
    reporter = make_user("Reporter")
    target = make_user("Target")
    invalid_type = client.post(
        "/api/v1/safety/reports",
        json={
            "target_id": str(target.id),
            "target_type": "general",
            "reason": "harassment",
        },
        headers=auth_headers(reporter),
    )
    assert invalid_type.status_code == 422
    assert invalid_type.get_json()["error"] == "invalid_target_type"

    invalid_ref = client.post(
        "/api/v1/safety/reports",
        json={
            "target_id": str(target.id),
            "target_type": "message",
            "target_ref": "not-a-uuid",
            "reason": "harassment",
        },
        headers=auth_headers(reporter),
    )
    assert invalid_ref.status_code == 422
    assert invalid_ref.get_json()["error"] == "invalid_target_ref"


def test_duplicate_open_report_returns_existing_reference(client):
    reporter = make_user("Reporter")
    target = make_user("Target")
    payload = {
        "target_id": str(target.id),
        "reason": "harassment",
    }
    first = client.post(
        "/api/v1/safety/reports", json=payload, headers=auth_headers(reporter)
    )
    second = client.post(
        "/api/v1/safety/reports", json=payload, headers=auth_headers(reporter)
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.get_json()["id"] == first.get_json()["id"]
