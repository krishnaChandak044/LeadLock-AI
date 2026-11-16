"""
LeadLock AI — Customer CRUD Router
Customer management with lead score filtering and tenant isolation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models import Customer
from shared.schemas import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter(prefix="/tenants/{tenant_id}/customers", tags=["customers"])


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    tenant_id: UUID,
    lead_score: str | None = Query(None, pattern=r"^(COLD|WARM|HOT)$"),
    search: str | None = Query(None, min_length=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Customer]:
    """List customers for a tenant with optional filtering."""
    stmt = (
        select(Customer)
        .where(Customer.tenant_id == tenant_id)
        .order_by(Customer.last_contacted_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if lead_score:
        stmt = stmt.where(Customer.lead_score == lead_score)
    if search:
        stmt = stmt.where(
            Customer.phone_number.ilike(f"%{search}%")
            | Customer.name.ilike(f"%{search}%")
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/count")
async def count_customers(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Get customer counts by lead score."""
    stmt = (
        select(Customer.lead_score, func.count(Customer.id))
        .where(Customer.tenant_id == tenant_id)
        .group_by(Customer.lead_score)
    )
    result = await db.execute(stmt)
    counts = {row[0]: row[1] for row in result.all()}
    total = sum(counts.values())
    return {"total": total, **counts}


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    tenant_id: UUID,
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Customer:
    """Get a customer by ID."""
    stmt = select(Customer).where(
        Customer.id == customer_id,
        Customer.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    tenant_id: UUID,
    customer_id: UUID,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
) -> Customer:
    """Update a customer (lead score, name)."""
    stmt = select(Customer).where(
        Customer.id == customer_id,
        Customer.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)
    return customer
