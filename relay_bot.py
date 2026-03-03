import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
import json
import os

BOT_TOKEN = os.getenv("RELAY_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Set RELAY_BOT_TOKEN or BOT_TOKEN environment variable")
CONFIG_FILE = "relay_config.json"

PROXY = os.getenv("TELEGRAM_PROXY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("relay_bot")

if PROXY:
    session = AiohttpSession(proxy=PROXY)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"), session=session)
    log.info(f"Using proxy: {PROXY}")
else:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

dp = Dispatcher()

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "teacher_chat": None,
        "student_chat": None,
        "admin_id": None,
        "allowed_users": []
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()

async def is_admin(msg: Message) -> bool:
    user_id = msg.from_user.id
    
    if config.get("admin_id") == user_id:
        return True
    
    if user_id in config.get("allowed_users", []):
        return True
    
    if msg.chat.type in ["group", "supergroup"]:
        try:
            member = await bot.get_chat_member(msg.chat.id, user_id)
            return member.status in ["creator", "administrator"]
        except:
            return False
    
    return False

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    if not await is_admin(msg):
        return
    
    help_text = """
<b>Relay Bot - Бот-посредник</b>

<b>Команды для настройки:</b>
/setup - Показать текущие настройки
/set_teacher - Установить чат преподавателя (используйте в групповом чате)
/set_student - Установить чат ученика (используйте в групповом чате)
/add_admin - Добавить пользователя с правами управления (ответьте на его сообщение)
/remove_admin - Удалить пользователя из списка разрешённых (ответьте на его сообщение)
/help - Показать эту справку

<b>Как работает:</b>
1. Добавьте бота в два чата (препод и ученик)
2. В чате преподавателя напишите /set_teacher
3. В чате ученика напишите /set_student
4. Все сообщения будут автоматически пересылаться между чатами

<b>Безопасность:</b>
Только администраторы чатов и разрешённые пользователи могут управлять ботом
Обычные участники НЕ могут использовать команды бота
Первый, кто настроит бота, становится главным администратором
"""
    await msg.answer(help_text)

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    if not await is_admin(msg):
        return
    await cmd_start(msg)

@dp.message(Command("setup"))
async def cmd_setup(msg: Message):
    if not await is_admin(msg):
        return
    
    teacher = config.get("teacher_chat")
    student = config.get("student_chat")
    admin_id = config.get("admin_id")
    allowed_count = len(config.get("allowed_users", []))
    
    status = f"""
<b>Текущие настройки:</b>

Чат преподавателя: <code>{teacher if teacher else 'Не установлен'}</code>
Чат ученика: <code>{student if student else 'Не установлен'}</code>
Главный админ: <code>{admin_id if admin_id else 'Не установлен'}</code>
Разрешённых пользователей: {allowed_count}

{'Бот настроен и готов к работе!' if teacher and student else 'Необходимо настроить оба чата'}
"""
    await msg.answer(status)

@dp.message(Command("set_teacher"))
async def cmd_set_teacher(msg: Message):
    if not await is_admin(msg):
        await msg.answer("У вас нет прав для выполнения этой команды!")
        return
    
    if msg.chat.type not in ["group", "supergroup"]:
        await msg.answer("Эта команда работает только в групповых чатах!")
        return
    
    config["teacher_chat"] = msg.chat.id
    if not config.get("admin_id"):
        config["admin_id"] = msg.from_user.id
    save_config(config)
    
    await msg.answer(f"Чат преподавателя установлен!\nID: <code>{msg.chat.id}</code>\nНазвание: {msg.chat.title}")
    log.info(f"Teacher chat set: {msg.chat.id} ({msg.chat.title})")

@dp.message(Command("set_student"))
async def cmd_set_student(msg: Message):
    if not await is_admin(msg):
        await msg.answer("У вас нет прав для выполнения этой команды!")
        return
    
    if msg.chat.type not in ["group", "supergroup"]:
        await msg.answer("Эта команда работает только в групповых чатах!")
        return
    
    config["student_chat"] = msg.chat.id
    if not config.get("admin_id"):
        config["admin_id"] = msg.from_user.id
    save_config(config)
    
    await msg.answer(f"Чат ученика установлен!\nID: <code>{msg.chat.id}</code>\nНазвание: {msg.chat.title}")
    log.info(f"Student chat set: {msg.chat.id} ({msg.chat.title})")

@dp.message(Command("add_admin"))
async def cmd_add_admin(msg: Message):
    if msg.from_user.id != config.get("admin_id"):
        await msg.answer("Только главный администратор может добавлять разрешённых пользователей!")
        return
    
    if not msg.reply_to_message:
        await msg.answer("Ответьте этой командой на сообщение пользователя, которого хотите добавить!")
        return
    
    user_id = msg.reply_to_message.from_user.id
    user_name = msg.reply_to_message.from_user.full_name
    
    if "allowed_users" not in config:
        config["allowed_users"] = []
    
    if user_id in config["allowed_users"]:
        await msg.answer(f"Пользователь {user_name} уже в списке разрешённых!")
        return
    
    config["allowed_users"].append(user_id)
    save_config(config)
    
    await msg.answer(f"Пользователь {user_name} (ID: <code>{user_id}</code>) добавлен в список разрешённых!")
    log.info(f"Added allowed user: {user_id} ({user_name})")

@dp.message(Command("remove_admin"))
async def cmd_remove_admin(msg: Message):
    if msg.from_user.id != config.get("admin_id"):
        await msg.answer("Только главный администратор может удалять разрешённых пользователей!")
        return
    
    if not msg.reply_to_message:
        await msg.answer("Ответьте этой командой на сообщение пользователя, которого хотите удалить!")
        return
    
    user_id = msg.reply_to_message.from_user.id
    user_name = msg.reply_to_message.from_user.full_name
    
    if "allowed_users" not in config:
        config["allowed_users"] = []
    
    if user_id not in config["allowed_users"]:
        await msg.answer(f"Пользователь {user_name} не в списке разрешённых!")
        return
    
    config["allowed_users"].remove(user_id)
    save_config(config)
    
    await msg.answer(f"Пользователь {user_name} (ID: <code>{user_id}</code>) удалён из списка разрешённых!")
    log.info(f"Removed allowed user: {user_id} ({user_name})")

async def forward_message(msg: Message, target_chat_id: int, source_name: str):
    try:
        header = f"<b>Сообщение от {source_name}:</b>\n\n"
        
        if msg.text:
            await bot.send_message(target_chat_id, header + msg.text)
        elif msg.photo:
            caption = header + (msg.caption or "")
            await bot.send_photo(target_chat_id, msg.photo[-1].file_id, caption=caption)
        elif msg.video:
            caption = header + (msg.caption or "")
            await bot.send_video(target_chat_id, msg.video.file_id, caption=caption)
        elif msg.document:
            caption = header + (msg.caption or "")
            await bot.send_document(target_chat_id, msg.document.file_id, caption=caption)
        elif msg.voice:
            await bot.send_voice(target_chat_id, msg.voice.file_id, caption=header)
        elif msg.audio:
            caption = header + (msg.caption or "")
            await bot.send_audio(target_chat_id, msg.audio.file_id, caption=caption)
        elif msg.video_note:
            await bot.send_video_note(target_chat_id, msg.video_note.file_id)
            await bot.send_message(target_chat_id, header + "Видеосообщение")
        elif msg.sticker:
            await bot.send_sticker(target_chat_id, msg.sticker.file_id)
            await bot.send_message(target_chat_id, header + "Стикер")
        else:
            await bot.send_message(target_chat_id, header + "[Неподдерживаемый тип сообщения]")
        
        log.info(f"Message forwarded from {source_name} to {target_chat_id}")
        return True
    except Exception as e:
        log.error(f"Error forwarding message: {e}")
        return False

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(msg: Message):
    teacher_chat = config.get("teacher_chat")
    student_chat = config.get("student_chat")
    
    if not teacher_chat or not student_chat:
        return
    
    if msg.text and msg.text.startswith('/'):
        return
    
    if msg.chat.id == teacher_chat:
        await forward_message(msg, student_chat, "преподавателя")
    elif msg.chat.id == student_chat:
        await forward_message(msg, teacher_chat, "ученика")

async def main():
    log.info("Relay Bot zapushen!")
    log.info(f"Teacher chat: {config.get('teacher_chat')}")
    log.info(f"Student chat: {config.get('student_chat')}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
