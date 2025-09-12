
import time
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.last_time: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        now = time.time()
        user_id = event.from_user.id
        last = self.last_time.get(user_id, 0)
        if now - last < self.rate_limit:
            await event.answer("⚡ Слишком часто! Подождите немного.")
            return
        self.last_time[user_id] = now
        return await handler(event, data)
