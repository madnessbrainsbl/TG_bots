from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select

from keyboards.reply import (
    main_menu_kb,
    admin_menu_kb,
    content_manager_kb,
    moderator_menu_kb,
)
from db import get_session
from db.models import User, UserRole

router = Router(name=__name__)

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в MLM-бота!</b>\n\n"
    "<b>Куда Мы Идем: Миссия Помогать 150 000 Людям в Год 🌟</b>\n\n"
    "Каждый из нас сталкивается с вызовами, которые порой кажутся непреодолимыми. "
    "Для многих людей долговые обязательства становятся таким вызовом, затмевающим радость жизни "
    "и ограничивающим возможности. Но мы твёрдо верим, что вместе мы можем изменить эту ситуацию "
    "и вернуть людям свободу и уверенность в завтрашнем дне. 🌈\n"
    "Наша цель — помогать 150 000 людям в год списать их долги. Это амбициозная задача, "
    "но мы убеждены, что она достижима. Почему? Потому что у нас есть вы — команда единомышленников, "
    "готовых внести свой вклад в это важное дело. 🤝\n\n"
    "<b>Почему это важно?</b>\n"
    "Долги могут стать настоящим бременем, влияющим на все аспекты жизни человека. "
    "Они ограничивают возможности, создают стресс и мешают двигаться вперёд. "
    "Освобождение от долгов — это не просто финансовая выгода, это новый старт, шанс на лучшее будущее. 🚀\n\n"
    "<b>Как мы этого достигнем?</b>\n"
    "1. <b>Командная работа:</b> Только объединив усилия, мы сможем достичь нашей цели. "
    "Каждый из вас — важная часть этой миссии. Ваша энергия, идеи и поддержка — это то, что движет нас вперёд. 💪\n"
    "2. <b>Индивидуальный подход:</b> Каждая история уникальна, и мы будем искать решения, "
    "которые подходят именно для конкретного человека. Это требует внимания и заботы, "
    "но именно так мы сможем добиться настоящих изменений. ❤️\n"
    "3. <b>Образование и поддержка:</b> Мы будем не только помогать списывать долги, "
    "но и обучать людей, как избежать их в будущем. Знания — это сила, и мы хотим, "
    "чтобы каждый наш клиент чувствовал себя уверенно и защищённо. 📚\n\n"
    "<b>Вместе мы можем больше 🌟</b>\n"
    "Мы верим, что с вашей помощью мы сможем изменить жизни тысяч людей. "
    "Это не просто задача — это миссия, которая вдохновляет и наполняет смыслом каждый наш день. "
    "Давайте вместе сделаем этот мир лучше, шаг за шагом, помогая тем, кто в этом нуждается. 🌍\n\n"
    "<b>Вместе мы сможем достичь невероятного. Я горжусь тем, что иду по этому пути с вами. 🙌</b>\n\n"
    "С уважением и верой в успех,\n"
    "@alexey62ryazan"
)


async def get_role_menu(role: UserRole):
    """Возвращает клавиатуру в зависимости от роли пользователя."""
    if role == UserRole.admin:
        return admin_menu_kb()
    elif role == UserRole.content:
        return content_manager_kb()
    elif role == UserRole.moderator:
        return moderator_menu_kb()
    # все остальные роли → обычное меню
    return main_menu_kb(role)


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    """При /start создаём пользователя (все — партнёры), показываем меню по роли."""
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Новый пользователь → сразу партнёр
            user = User(
                tg_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                role=UserRole.partner,
            )
            session.add(user)
            await session.commit()
            role = UserRole.partner
        else:
            role = user.role

    kb = await get_role_menu(role)
    await message.answer(WELCOME_TEXT, reply_markup=kb)


@router.message(Command("menu"))
async def on_menu(message: Message) -> None:
    """Открыть меню повторно с учетом роли."""
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        role = user.role if user else UserRole.partner

    kb = await get_role_menu(role)
    await message.answer("Главное меню открыто 👇", reply_markup=kb)
