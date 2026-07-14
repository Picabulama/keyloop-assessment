from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import InventoryAction, Vehicle, VehicleStatus
from app.schemas import InventoryActionCreate, VehicleCreate, VehicleUpdate


def days_in_inventory(vehicle: Vehicle, today: Optional[date] = None) -> int:
    today = today or date.today()
    return (today - vehicle.date_received).days


def is_aging(vehicle: Vehicle, today: Optional[date] = None) -> bool:
    return days_in_inventory(vehicle, today) > settings.aging_threshold_days


def get_vehicle(db: Session, vehicle_id: str) -> Optional[Vehicle]:
    return db.get(Vehicle, vehicle_id)


def get_vehicle_by_vin(db: Session, vin: str) -> Optional[Vehicle]:
    return db.execute(select(Vehicle).where(Vehicle.vin == vin)).scalar_one_or_none()


def list_vehicles(
    db: Session,
    *,
    make: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[VehicleStatus] = None,
    dealership_id: Optional[str] = None,
    min_age_days: Optional[int] = None,
    max_age_days: Optional[int] = None,
    aging_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Vehicle], int]:
    stmt = select(Vehicle)

    if make:
        stmt = stmt.where(Vehicle.make.ilike(f"%{make}%"))
    if model:
        stmt = stmt.where(Vehicle.model.ilike(f"%{model}%"))
    if status:
        stmt = stmt.where(Vehicle.status == status)
    if dealership_id:
        stmt = stmt.where(Vehicle.dealership_id == dealership_id)

    # date_received cutoffs are derived from "days_in_inventory = today - date_received";
    # subtract one extra day so the comparison matches the strict `> N days` semantics used by is_aging().
    today = date.today()

    if min_age_days is not None:
        cutoff = today.fromordinal(today.toordinal() - min_age_days)
        stmt = stmt.where(Vehicle.date_received <= cutoff)
    if max_age_days is not None:
        cutoff = today.fromordinal(today.toordinal() - max_age_days)
        stmt = stmt.where(Vehicle.date_received >= cutoff)
    if aging_only:
        cutoff = today.fromordinal(today.toordinal() - settings.aging_threshold_days - 1)
        stmt = stmt.where(Vehicle.date_received <= cutoff)

    total = len(db.execute(stmt).scalars().all())

    stmt = stmt.order_by(Vehicle.date_received.asc()).limit(limit).offset(offset)
    items = list(db.execute(stmt).scalars().all())
    return items, total


def create_vehicle(db: Session, vehicle_in: VehicleCreate) -> Vehicle:
    vehicle = Vehicle(**vehicle_in.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle(db: Session, vehicle: Vehicle, vehicle_in: VehicleUpdate) -> Vehicle:
    for field, value in vehicle_in.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle: Vehicle) -> None:
    db.delete(vehicle)
    db.commit()


def create_action(db: Session, vehicle: Vehicle, action_in: InventoryActionCreate) -> InventoryAction:
    action = InventoryAction(vehicle_id=vehicle.id, **action_in.model_dump())
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def list_actions(db: Session, vehicle_id: str) -> list[InventoryAction]:
    stmt = (
        select(InventoryAction)
        .where(InventoryAction.vehicle_id == vehicle_id)
        .order_by(InventoryAction.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def aging_summary(db: Session, *, dealership_id: Optional[str] = None) -> dict:
    stmt = select(Vehicle).where(Vehicle.status == VehicleStatus.IN_STOCK)
    if dealership_id:
        stmt = stmt.where(Vehicle.dealership_id == dealership_id)
    vehicles = list(db.execute(stmt).scalars().all())

    total = len(vehicles)
    aging = [v for v in vehicles if is_aging(v)]
    oldest = max((days_in_inventory(v) for v in vehicles), default=None)

    return {
        "aging_threshold_days": settings.aging_threshold_days,
        "total_vehicles": total,
        "aging_vehicle_count": len(aging),
        "aging_percentage": round((len(aging) / total) * 100, 2) if total else 0.0,
        "oldest_days_in_inventory": oldest,
    }
