# check_cycle.py
import asyncio

from sqlalchemy import select

from db import AsyncSessionLocal
from db_models.verification_cycle import VerificationCycle


async def main():
    async with AsyncSessionLocal() as session:
        # create one cycle
        cycle = VerificationCycle(tag="Q4 2025")
        session.add(cycle)
        await session.commit()
        await session.refresh(cycle)
        print("Created cycle:", cycle.id, cycle.tag, cycle.status)

        # query it back
        result = await session.execute(select(VerificationCycle))
        cycles = result.scalars().all()
        print("All cycles:", [(c.id, c.tag, c.status) for c in cycles])


if __name__ == "__main__":
    asyncio.run(main())
