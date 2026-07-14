import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

logger = logging.getLogger("inventory.actions")

router = APIRouter(prefix="/vehicles/{vehicle_id}/actions", tags=["actions"])


@router.get("", response_model=list[schemas.InventoryActionRead])
def list_actions(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = crud.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return crud.list_actions(db, vehicle_id)


@router.post("", response_model=schemas.InventoryActionRead, status_code=201)
def create_action(vehicle_id: str, action_in: schemas.InventoryActionCreate, db: Session = Depends(get_db)):
    vehicle = crud.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    action = crud.create_action(db, vehicle, action_in)
    logger.info(
        "inventory_action_logged",
        extra={"vehicle_id": vehicle_id, "action_id": action.id, "status": action.status},
    )
    return action
