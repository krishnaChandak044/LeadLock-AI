import asyncio
from shared.database import async_session_factory
from sqlalchemy import update
from shared.models import CommunicationSession

async def main():
    async with async_session_factory() as session:
        await session.execute(update(CommunicationSession).values(is_human_takeover=False))
        await session.commit()
        print("Successfully reset all sessions back to AI mode!")

if __name__ == "__main__":
    asyncio.run(main())
