from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Vehicle, VehicleStatus

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_vehicle(db_session, *, days_ago=10, vin="TESTVIN0000000001", make="Honda", model="Civic", **overrides):
    vehicle = Vehicle(
        vin=vin,
        make=make,
        model=model,
        year=2022,
        price=20000,
        status=VehicleStatus.IN_STOCK,
        date_received=date.today() - timedelta(days=days_ago),
        **overrides,
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)
    return vehicle
