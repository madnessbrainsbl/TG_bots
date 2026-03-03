
from aiogram import Bot

async def notify_user(bot: Bot, user_id: int, text: str):
    """Отправка уведомления пользователю."""
    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

async def notify_admins(bot: Bot, admin_ids: list[int], text: str):
    """Отправка уведомления всем администраторам."""
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            print(f"Ошибка при отправке сообщения админу {admin_id}: {e}")
