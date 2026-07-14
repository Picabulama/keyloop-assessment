from tests.conftest import make_vehicle


def test_log_action_for_aging_vehicle(client, db_session):
    vehicle = make_vehicle(db_session, vin="AGE1", days_ago=120)

    resp = client.post(
        f"/vehicles/{vehicle.id}/actions",
        json={"status": "price_reduction_planned", "note": "Reduce by $1000", "created_by": "manager1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "price_reduction_planned"
    assert body["vehicle_id"] == vehicle.id


def test_list_actions_most_recent_first(client, db_session):
    vehicle = make_vehicle(db_session, vin="AGE2", days_ago=120)

    client.post(f"/vehicles/{vehicle.id}/actions", json={"status": "no_action"})
    client.post(f"/vehicles/{vehicle.id}/actions", json={"status": "price_reduction_planned"})

    resp = client.get(f"/vehicles/{vehicle.id}/actions")
    assert resp.status_code == 200
    actions = resp.json()
    assert len(actions) == 2
    assert actions[0]["status"] == "price_reduction_planned"


def test_action_persists_and_appears_as_latest_action_on_vehicle(client, db_session):
    vehicle = make_vehicle(db_session, vin="AGE3", days_ago=120)
    client.post(f"/vehicles/{vehicle.id}/actions", json={"status": "transfer_planned", "note": "Move to lot B"})

    resp = client.get(f"/vehicles/{vehicle.id}")
    assert resp.status_code == 200
    latest = resp.json()["latest_action"]
    assert latest is not None
    assert latest["status"] == "transfer_planned"
    assert latest["note"] == "Move to lot B"


def test_action_on_missing_vehicle_returns_404(client):
    resp = client.post("/vehicles/does-not-exist/actions", json={"status": "no_action"})
    assert resp.status_code == 404
