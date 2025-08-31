import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import admin, user
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(admin.router)
dp.include_router(user.router)

if __name__ == "__main__":
    try:
        asyncio.run(dp.start_polling(bot))
    except KeyboardInterrupt:
        print("Бот выключен")
