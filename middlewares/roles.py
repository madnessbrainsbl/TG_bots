from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from db import get_session
from db.models import User, UserRole
from sqlalchemy.future import select

class RoleMiddleware(BaseMiddleware):
    def __init__(self, allowed_roles: list[UserRole] = None):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        async with get_session() as session:
            result = await session.execute(select(User).where(User.tg_id == event.from_user.id))
            user = result.scalars().first()

        if not user:
            await event.answer("❌ Сначала зарегистрируйтесь через /start")
            return
        if self.allowed_roles and user.role not in self.allowed_roles:
            await event.answer("⛔ У вас нет доступа к этой команде")
            return

        data["user"] = user
        return await handler(event, data)
