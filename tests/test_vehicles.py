from datetime import date, timedelta

from tests.conftest import make_vehicle


def test_create_vehicle(client):
    payload = {
        "vin": "1HGCM82633A004352",
        "make": "Honda",
        "model": "Accord",
        "year": 2023,
        "price": 28900,
        "date_received": str(date.today()),
    }
    resp = client.post("/vehicles", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["vin"] == payload["vin"]
    assert body["days_in_inventory"] == 0
    assert body["is_aging"] is False


def test_create_vehicle_duplicate_vin_rejected(client):
    payload = {
        "vin": "1HGCM82633A004352",
        "make": "Honda",
        "model": "Accord",
        "year": 2023,
        "price": 28900,
        "date_received": str(date.today()),
    }
    assert client.post("/vehicles", json=payload).status_code == 201
    resp = client.post("/vehicles", json=payload)
    assert resp.status_code == 409


def test_list_vehicles_filter_by_make(client, db_session):
    make_vehicle(db_session, vin="VIN1", make="Honda", model="Civic", days_ago=5)
    make_vehicle(db_session, vin="VIN2", make="Toyota", model="Corolla", days_ago=5)

    resp = client.get("/vehicles", params={"make": "Honda"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["make"] == "Honda"


def test_aging_stock_identification(client, db_session):
    make_vehicle(db_session, vin="FRESH1", days_ago=10)
    make_vehicle(db_session, vin="AGING1", days_ago=91)
    make_vehicle(db_session, vin="AGING2", days_ago=200)

    resp = client.get("/vehicles", params={"aging_only": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    vins = {v["vin"] for v in body["items"]}
    assert vins == {"AGING1", "AGING2"}
    for item in body["items"]:
        assert item["is_aging"] is True
        assert item["days_in_inventory"] > 90


def test_aging_boundary_is_exclusive_at_exactly_90_days(client, db_session):
    make_vehicle(db_session, vin="EXACT90", days_ago=90)

    resp = client.get("/vehicles", params={"aging_only": True})
    assert resp.json()["total"] == 0


def test_aging_summary(client, db_session):
    make_vehicle(db_session, vin="FRESH1", days_ago=10)
    make_vehicle(db_session, vin="AGING1", days_ago=95)

    resp = client.get("/vehicles/aging-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_vehicles"] == 2
    assert body["aging_vehicle_count"] == 1
    assert body["aging_percentage"] == 50.0
    assert body["oldest_days_in_inventory"] == 95


def test_get_vehicle_not_found(client):
    resp = client.get("/vehicles/does-not-exist")
    assert resp.status_code == 404


def test_update_vehicle(client, db_session):
    vehicle = make_vehicle(db_session, vin="UPD1")
    resp = client.patch(f"/vehicles/{vehicle.id}", json={"price": 15999})
    assert resp.status_code == 200
    assert resp.json()["price"] == 15999


def test_delete_vehicle(client, db_session):
    vehicle = make_vehicle(db_session, vin="DEL1")
    resp = client.delete(f"/vehicles/{vehicle.id}")
    assert resp.status_code == 204
    assert client.get(f"/vehicles/{vehicle.id}").status_code == 404


def test_age_range_filters(client, db_session):
    make_vehicle(db_session, vin="A", days_ago=5)
    make_vehicle(db_session, vin="B", days_ago=50)
    make_vehicle(db_session, vin="C", days_ago=150)

    resp = client.get("/vehicles", params={"min_age_days": 30, "max_age_days": 100})
    assert resp.status_code == 200
    vins = {v["vin"] for v in resp.json()["items"]}
    assert vins == {"B"}
