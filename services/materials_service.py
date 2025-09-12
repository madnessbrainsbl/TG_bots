from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Material

async def add_material(session: AsyncSession, title: str, content: str):
    m = Material(title=title, content=content)
    session.add(m)
    await session.commit()
    return m

async def list_active_materials(session: AsyncSession):
    q = await session.execute(select(Material).where(Material.is_active == True))
    return q.scalars().all()

async def deactivate_material(session: AsyncSession, material_id: int):
    q = await session.execute(select(Material).where(Material.id == material_id))
    m = q.scalar_one()
    m.is_active = False
    await session.commit()
    return m
