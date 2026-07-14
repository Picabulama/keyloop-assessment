"""Seed the inventory database with sample dealership stock, including aging vehicles.

Run with: python -m scripts.seed_data
"""
from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app.models import ActionStatus, InventoryAction, Vehicle, VehicleStatus

SAMPLE_VEHICLES = [
    dict(vin="1HGCM82633A004352", make="Honda", model="Accord", trim="EX-L", year=2023,
         color="Silver", price=28900, mileage=1200, days_ago=12),
    dict(vin="2T1BURHE0JC014394", make="Toyota", model="Corolla", trim="SE", year=2022,
         color="Blue", price=21500, mileage=8300, days_ago=45),
    dict(vin="3FA6P0H74HR123456", make="Ford", model="Fusion", trim="SEL", year=2021,
         color="Black", price=19900, mileage=22000, days_ago=95),
    dict(vin="1G1ZD5ST8JF123789", make="Chevrolet", model="Malibu", trim="LT", year=2021,
         color="White", price=18500, mileage=25400, days_ago=132),
    dict(vin="5YJ3E1EA7JF001234", make="Tesla", model="Model 3", trim="Long Range", year=2023,
         color="Red", price=41900, mileage=3100, days_ago=5),
    dict(vin="JTDKARFU4J3123456", make="Toyota", model="Prius", trim="LE", year=2020,
         color="Gray", price=17900, mileage=41000, days_ago=180),
    dict(vin="1FTFW1E50JFA12345", make="Ford", model="F-150", trim="XLT", year=2022,
         color="Blue", price=36900, mileage=15200, days_ago=63),
    dict(vin="WBA8E9G59JNU12345", make="BMW", model="3 Series", trim="330i", year=2021,
         color="Black", price=29900, mileage=19800, days_ago=110),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Vehicle).count() > 0:
            print("Database already has vehicles; skipping seed.")
            return

        today = date.today()
        for entry in SAMPLE_VEHICLES:
            days_ago = entry.pop("days_ago")
            vehicle = Vehicle(
                status=VehicleStatus.IN_STOCK,
                date_received=today - timedelta(days=days_ago),
                **entry,
            )
            db.add(vehicle)
            db.flush()

            if days_ago > 90:
                db.add(
                    InventoryAction(
                        vehicle_id=vehicle.id,
                        status=ActionStatus.PRICE_REDUCTION_PLANNED,
                        note="Flagged by aging stock report; manager to review pricing.",
                        created_by="seed-script",
                    )
                )

        db.commit()
        print(f"Seeded {len(SAMPLE_VEHICLES)} vehicles.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
