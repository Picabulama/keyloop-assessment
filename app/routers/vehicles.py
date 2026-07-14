import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.models import VehicleStatus

logger = logging.getLogger("inventory.vehicles")

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _to_read_model(vehicle) -> schemas.VehicleRead:
    latest_action = vehicle.actions[0] if vehicle.actions else None
    return schemas.VehicleRead(
        **{c.name: getattr(vehicle, c.name) for c in vehicle.__table__.columns},
        days_in_inventory=crud.days_in_inventory(vehicle),
        is_aging=crud.is_aging(vehicle),
        latest_action=schemas.InventoryActionRead.model_validate(latest_action) if latest_action else None,
    )


@router.get("", response_model=schemas.VehicleListResponse)
def list_vehicles(
    make: Optional[str] = Query(default=None, description="Filter by make (partial match)"),
    model: Optional[str] = Query(default=None, description="Filter by model (partial match)"),
    status: Optional[VehicleStatus] = Query(default=None),
    dealership_id: Optional[str] = Query(default=None),
    min_age_days: Optional[int] = Query(default=None, ge=0, description="Minimum days in inventory"),
    max_age_days: Optional[int] = Query(default=None, ge=0, description="Maximum days in inventory"),
    aging_only: bool = Query(default=False, description="Only return vehicles in aging stock (>90 days)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = crud.list_vehicles(
        db,
        make=make,
        model=model,
        status=status,
        dealership_id=dealership_id,
        min_age_days=min_age_days,
        max_age_days=max_age_days,
        aging_only=aging_only,
        limit=limit,
        offset=offset,
    )
    return schemas.VehicleListResponse(
        total=total, limit=limit, offset=offset, items=[_to_read_model(v) for v in items]
    )


@router.get("/aging-summary", response_model=schemas.AgingSummary)
def get_aging_summary(dealership_id: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    return crud.aging_summary(db, dealership_id=dealership_id)


@router.get("/{vehicle_id}", response_model=schemas.VehicleRead)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = crud.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return _to_read_model(vehicle)


@router.post("", response_model=schemas.VehicleRead, status_code=201)
def create_vehicle(vehicle_in: schemas.VehicleCreate, db: Session = Depends(get_db)):
    if crud.get_vehicle_by_vin(db, vehicle_in.vin):
        raise HTTPException(status_code=409, detail="A vehicle with this VIN already exists")
    try:
        vehicle = crud.create_vehicle(db, vehicle_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A vehicle with this VIN already exists")
    logger.info("vehicle_created", extra={"vehicle_id": vehicle.id, "vin": vehicle.vin})
    return _to_read_model(vehicle)


@router.patch("/{vehicle_id}", response_model=schemas.VehicleRead)
def update_vehicle(vehicle_id: str, vehicle_in: schemas.VehicleUpdate, db: Session = Depends(get_db)):
    vehicle = crud.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    vehicle = crud.update_vehicle(db, vehicle, vehicle_in)
    logger.info("vehicle_updated", extra={"vehicle_id": vehicle.id})
    return _to_read_model(vehicle)


@router.delete("/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = crud.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    crud.delete_vehicle(db, vehicle)
    logger.info("vehicle_deleted", extra={"vehicle_id": vehicle_id})
    return None
