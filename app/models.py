import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class VehicleStatus(str, enum.Enum):
    IN_STOCK = "in_stock"
    PENDING_SALE = "pending_sale"
    SOLD = "sold"


class ActionStatus(str, enum.Enum):
    NO_ACTION = "no_action"
    PRICE_REDUCTION_PLANNED = "price_reduction_planned"
    TRANSFER_PLANNED = "transfer_planned"
    PROMOTION_PLANNED = "promotion_planned"
    WHOLESALE_PLANNED = "wholesale_planned"
    OTHER = "other"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True, default=generate_uuid)
    dealership_id = Column(String, nullable=False, index=True, default="default")
    vin = Column(String, unique=True, nullable=False, index=True)
    make = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    trim = Column(String, nullable=True)
    year = Column(Integer, nullable=False, index=True)
    color = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    mileage = Column(Integer, nullable=True)
    status = Column(Enum(VehicleStatus), nullable=False, default=VehicleStatus.IN_STOCK, index=True)
    date_received = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    actions = relationship(
        "InventoryAction", back_populates="vehicle", cascade="all, delete-orphan", order_by="desc(InventoryAction.created_at)"
    )


class InventoryAction(Base):
    __tablename__ = "inventory_actions"

    id = Column(String, primary_key=True, default=generate_uuid)
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=False, index=True)
    status = Column(Enum(ActionStatus), nullable=False, default=ActionStatus.NO_ACTION)
    note = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    vehicle = relationship("Vehicle", back_populates="actions")
