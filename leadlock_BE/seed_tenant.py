import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from shared.models import Tenant
from shared.config import settings

async def seed():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            tenant = Tenant(
                id=uuid4(),
                business_name="Demo Auto Dealership",
                vertical_type="AUTOMOTIVE",
                ai_system_prompt="You are an AI sales assistant for an automotive dealership. Your goal is to qualify leads and schedule test drives. Only recommend cars from our inventory.",
                whatsapp_session_id="session_01",
                openwa_base_url="http://localhost:2785"
            )
            session.add(tenant)
            await session.commit()
            print(f"Created tenant: {tenant.id}")
        else:
            print(f"Tenant already exists: {tenant.id}")

if __name__ == "__main__":
    asyncio.run(seed())
