
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from aiogram.fsm.context import FSMContext

class FSMAutoCleanupMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        fsm: FSMContext = data.get("state")
        try:
            result = await handler(event, data)
            return result
        finally:
            if fsm:
                await fsm.clear()
