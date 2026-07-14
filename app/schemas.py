from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import ActionStatus, VehicleStatus


class VehicleBase(BaseModel):
    vin: str = Field(..., min_length=1, max_length=32)
    make: str
    model: str
    trim: Optional[str] = None
    year: int = Field(..., ge=1900, le=2100)
    color: Optional[str] = None
    price: float = Field(..., ge=0)
    mileage: Optional[int] = Field(default=None, ge=0)
    status: VehicleStatus = VehicleStatus.IN_STOCK
    date_received: date
    dealership_id: str = "default"


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    trim: Optional[str] = None
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    color: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    mileage: Optional[int] = Field(default=None, ge=0)
    status: Optional[VehicleStatus] = None
    date_received: Optional[date] = None
    dealership_id: Optional[str] = None


class InventoryActionBase(BaseModel):
    status: ActionStatus
    note: Optional[str] = Field(default=None, max_length=2000)
    created_by: Optional[str] = None


class InventoryActionCreate(InventoryActionBase):
    pass


class InventoryActionRead(InventoryActionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vehicle_id: str
    created_at: datetime


class VehicleRead(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    days_in_inventory: int
    is_aging: bool
    latest_action: Optional[InventoryActionRead] = None


class VehicleListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[VehicleRead]


class AgingSummary(BaseModel):
    aging_threshold_days: int
    total_vehicles: int
    aging_vehicle_count: int
    aging_percentage: float
    oldest_days_in_inventory: Optional[int] = None
