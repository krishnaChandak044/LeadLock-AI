"""
LeadLock AI — Tenant CRUD Router
Full CRUD for multi-tenant management.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models import Tenant
from shared.schemas import TenantCreate, TenantUpdate, TenantResponse

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> list[Tenant]:
    """List all tenants, optionally filtered by active status."""
    stmt = select(Tenant).order_by(Tenant.created_at.desc())
    if active_only:
        stmt = stmt.where(Tenant.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Create a new tenant."""
    tenant = Tenant(
        business_name=data.business_name,
        vertical_type=data.vertical_type,
        ai_system_prompt=data.ai_system_prompt,
        whatsapp_session_id=data.whatsapp_session_id,
        openwa_base_url=data.openwa_base_url,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Get a tenant by ID."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Update a tenant."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=204, response_class=Response)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Soft-delete a tenant (deactivate)."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.is_active = False
    await db.commit()
    return Response(status_code=204)
