# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import settings
from db import init_db
from monitoring.logger import setup_logging  # наш кастомный логгер

from handlers import (
    admin,
    bonuses,
    common,
    content,
    deals,
    instructions,
    leads,
    partners,
    payouts,
    profile,
    reviews,
    roles,
    statistics,
)
from mlm import tree  # отдельный модуль MLM-логики


async def main():
    # Проверяем наличие токена
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    # Логируем приветственное сообщение, если оно есть
    if hasattr(settings, "welcome_message") and settings.welcome_message:
        logging.info(settings.welcome_message)

    # Инициализация базы данных
    await init_db()

    # Создаём бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(common.router)
    dp.include_router(statistics.router)
    dp.include_router(profile.router)
    dp.include_router(leads.router)
    dp.include_router(deals.router)
    dp.include_router(bonuses.router)
    dp.include_router(payouts.router)
    dp.include_router(content.router)
    dp.include_router(instructions.router)
    dp.include_router(admin.router)
    dp.include_router(partners.router)
    dp.include_router(reviews.router)
    dp.include_router(roles.router)
    dp.include_router(tree.router)  # MLM

    logging.info(f"Бот запущен: @{(await bot.me()).username}")

    # Стартуем пуллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    setup_logging(app_name="mlm_bot")  # ✅ подключаем наш логгер
    asyncio.run(main())
