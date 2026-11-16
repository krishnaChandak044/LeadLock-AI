"""
LeadLock AI — Inventory CRUD Router
Schema-agnostic inventory management with JSONB support.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models import Inventory
from shared.schemas import InventoryCreate, InventoryUpdate, InventoryResponse
from shared.schemas.inventory import InventoryBulkCreate

router = APIRouter(prefix="/tenants/{tenant_id}/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryResponse])
async def list_inventory(
    tenant_id: UUID,
    status: str | None = Query(None, pattern=r"^(AVAILABLE|RESERVED|SOLD)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Inventory]:
    """List inventory items for a tenant."""
    stmt = (
        select(Inventory)
        .where(Inventory.tenant_id == tenant_id)
        .order_by(Inventory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status:
        stmt = stmt.where(Inventory.status == status)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=InventoryResponse, status_code=201)
async def create_inventory(
    tenant_id: UUID,
    data: InventoryCreate,
    db: AsyncSession = Depends(get_db),
) -> Inventory:
    """Create a new inventory item."""
    item = Inventory(
        tenant_id=tenant_id,
        name=data.name,
        status=data.status,
        vertical_data=data.vertical_data,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/bulk", response_model=list[InventoryResponse], status_code=201)
async def bulk_create_inventory(
    tenant_id: UUID,
    data: InventoryBulkCreate,
    db: AsyncSession = Depends(get_db),
) -> list[Inventory]:
    """Bulk create inventory items."""
    items = []
    for item_data in data.items:
        item = Inventory(
            tenant_id=tenant_id,
            name=item_data.name,
            status=item_data.status,
            vertical_data=item_data.vertical_data,
        )
        db.add(item)
        items.append(item)

    await db.commit()
    for item in items:
        await db.refresh(item)
    return items


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory(
    tenant_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Inventory:
    """Get an inventory item by ID."""
    stmt = select(Inventory).where(
        Inventory.id == item_id,
        Inventory.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory(
    tenant_id: UUID,
    item_id: UUID,
    data: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> Inventory:
    """Update an inventory item."""
    stmt = select(Inventory).where(
        Inventory.id == item_id,
        Inventory.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204, response_class=Response)
async def delete_inventory(
    tenant_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete an inventory item."""
    stmt = select(Inventory).where(
        Inventory.id == item_id,
        Inventory.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    await db.delete(item)
    await db.commit()
    return Response(status_code=204)
