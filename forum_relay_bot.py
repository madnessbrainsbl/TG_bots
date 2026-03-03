import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
import json
import os
import re
from collections import defaultdict

BOT_TOKEN = os.getenv("FORUM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Set FORUM_BOT_TOKEN or BOT_TOKEN environment variable")
CONFIG_FILE = "forum_relay_config.json"

PROXY = os.getenv("TELEGRAM_PROXY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("forum_relay_bot")

if PROXY:
    session = AiohttpSession(proxy=PROXY)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"), session=session)
    log.info(f"Using proxy: {PROXY}")
else:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

dp = Dispatcher()

# Буфер для медиагрупп: media_group_id -> список сообщений
media_group_buffer = defaultdict(list)
media_group_timers = {}

MAX_MESSAGE_LENGTH = 4096

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "forum_chat": None,
        "forums": [],
        "admin_id": None,
        "allowed_users": [],
        "student_chats": {},
        "aliases": {},
        "participants": {}
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()
migrated = False
if "forums" not in config:
    config["forums"] = []
    migrated = True
if config.get("forum_chat") and config["forum_chat"] not in config["forums"]:
    config["forums"].append(config["forum_chat"])
    migrated = True
sc = config.get("student_chats", {})
for _cid, _info in sc.items():
    if "forum_chat" not in _info:
        _info["forum_chat"] = config.get("forum_chat")
        migrated = True
if "aliases" not in config:
    config["aliases"] = {}
    migrated = True
if "participants" not in config:
    config["participants"] = {}
    migrated = True
if migrated:
    save_config(config)
pending_links = {}
awaiting_link_input = set()
pending_alias = {}
pending_add_participant = {}

ALLOWED_USERNAMES = {"infofizik_bot"}

# Разрешённые слова (не ники) - языки программирования, термины и т.д.
ALLOWED_WORDS = {
    "python", "java", "javascript", "typescript", "html", "css", "php", "ruby", "swift",
    "kotlin", "rust", "golang", "sql", "mysql", "postgresql", "mongodb", "redis",
    "react", "vue", "angular", "node", "express", "django", "flask", "spring",
    "docker", "kubernetes", "linux", "windows", "macos", "android", "ios",
    "git", "github", "gitlab", "api", "rest", "graphql", "json", "xml",
    "http", "https", "ftp", "ssh", "tcp", "udp", "dns", "ssl", "tls",
    "cpu", "gpu", "ram", "ssd", "hdd", "usb", "hdmi", "wifi", "bluetooth",
    "hello", "world", "test", "debug", "error", "warning", "info",
    "true", "false", "null", "none", "undefined", "nan",
    "print", "return", "import", "export", "class", "function", "def", "var", "let", "const",
    "for", "while", "loop", "break", "continue", "pass",
    "try", "catch", "except", "finally", "throw", "raise",
    "async", "await", "promise", "callback",
    "array", "list", "dict", "map", "set", "tuple", "string", "int", "float", "bool",
    "file", "open", "read", "write", "close", "save", "load", "delete",
    "user", "admin", "root", "guest", "login", "logout", "password", "email",
    "data", "database", "table", "query", "select", "insert", "update",
    "server", "client", "request", "response", "get", "post", "put", "patch",
    "start", "stop", "run", "build", "deploy", "install", "config",
    "log", "logs", "debug", "trace", "level",
    "ok", "yes", "no", "on", "off",
}
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
# Телефон: допускаем +, пробелы, дефисы и скобки; проверяем, что цифр >= 10
PHONE_PATTERN = re.compile(r"(?<!\w)(\+?\d[\d\s\-\(\)]{6,}\d)(?!\w)")


def is_allowed_username(raw: str) -> bool:
    if not raw:
        return False
    name = raw.lstrip("@").lower()
    return name in ALLOWED_USERNAMES


def has_phone_number(text: str) -> bool:
    if not text:
        return False
    for match in PHONE_PATTERN.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if len(digits) >= 10:
            return True
    return False


def strip_allowed_mentions(text: str) -> str:
    cleaned = text
    for uname in ALLOWED_USERNAMES:
        cleaned = re.sub(rf"@?{re.escape(uname)}", "", cleaned, flags=re.IGNORECASE)
    return cleaned

def build_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Настройки", callback_data="show_setup"), InlineKeyboardButton(text="Ученики", callback_data="list_students")],
        [InlineKeyboardButton(text="Форумы", callback_data="list_forums"), InlineKeyboardButton(text="Инструкция привязки", callback_data="show_link_help")],
        [InlineKeyboardButton(text="Имена", callback_data="names_menu"), InlineKeyboardButton(text="Администраторы", callback_data="admin_menu")]
    ])

def format_user_name(user, default_unknown: str) -> str:
    """Возвращает имя пользователя: alias если есть, иначе User XXXXX"""
    if not user:
        return default_unknown
    
    # Сначала проверяем alias (переименование)
    aliases = config.get("aliases", {})
    user_id_str = str(user.id)
    alias = aliases.get(user_id_str)
    if alias:
        return alias
    
    # Если нет alias — генерируем анонимное имя
    user_num = abs(user.id) % 100000
    return f"User {user_num}"

def update_participant(chat_id: int, user):
    if not user:
        return
    participants = config.get("participants", {})
    chat_key = str(chat_id)
    chat_part = participants.get(chat_key, {})
    user_key = str(user.id)
    name = getattr(user, "full_name", None) or getattr(user, "first_name", None) or getattr(user, "username", None) or user_key
    entry = chat_part.get(user_key, {})
    entry["name"] = name
    chat_part[user_key] = entry
    participants[chat_key] = chat_part
    config["participants"] = participants
    save_config(config)

def compose_setup_text() -> str:
    forums = config.get("forums", [])
    admin_id = config.get("admin_id")
    allowed_count = len(config.get("allowed_users", []))
    student_count = len(config.get("student_chats", {}))
    return f"""
<b>Текущие настройки:</b>

Форумов: {len(forums)}
Главный админ: <code>{admin_id if admin_id else 'Не установлен'}</code>
Разрешённых пользователей: {allowed_count}
Чатов учеников: {student_count}

{'Бот настроен и готов к работе!' if len(forums) > 0 else 'Необходимо настроить форум'}
"""

def build_students_kb() -> InlineKeyboardMarkup:
    data = config.get("student_chats", {})
    rows = []
    for cid, info in data.items():
        title = info.get("title", "")
        btn_text = f"{title or cid}: ссылка"
        rows.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"send_link:{cid}"),
            InlineKeyboardButton(text="Привязать", callback_data=f"bind_saved:{cid}")
        ])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="show_setup")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_students_kb_for_forum(forum_chat_id: int) -> InlineKeyboardMarkup:
    data = config.get("student_chats", {})
    rows = []
    for cid, info in data.items():
        if info.get("forum_chat") != forum_chat_id:
            continue
        title = info.get("title", "")
        thread_id = info.get("thread_id")
        link = build_topic_link(thread_id, forum_chat_id) if thread_id else ""
        open_btn = InlineKeyboardButton(text="Открыть", url=link) if link else InlineKeyboardButton(text="Открыть", callback_data="noop")
        rows.append([
            open_btn,
            InlineKeyboardButton(text="Ссылка в теме", callback_data=f"send_link:{cid}"),
            InlineKeyboardButton(text="Отвязать", callback_data=f"unlink:{cid}")
        ])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="list_forums")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_topic_link(thread_id: int, forum_chat_id: int) -> str:
    if not forum_chat_id:
        return ""
    cid = abs(int(forum_chat_id))
    internal_num = cid - 1000000000000 if cid > 1000000000000 else cid
    return f"https://t.me/c/{internal_num}/{thread_id}"

async def answer_safe(message: Message, text: str, **kwargs):
    try:
        await message.answer(text, **kwargs)
    except TelegramBadRequest as e:
        if "TOPIC_CLOSED" in str(e).upper():
            kwargs.pop("message_thread_id", None)
            await bot.send_message(message.chat.id, text, **kwargs)
        else:
            raise

def build_group_kb(chat_id: int) -> InlineKeyboardMarkup:
    chat_id_str = str(chat_id)
    data = config.get("student_chats", {})
    if chat_id_str in data:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ссылка темы", callback_data=f"send_link:{chat_id_str}")],
            [InlineKeyboardButton(text="Отвязать", callback_data=f"unlink:{chat_id_str}")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Привязать к сохраненной теме", callback_data="link_saved")],
            [InlineKeyboardButton(text="Ввести ID/ссылку", callback_data="enter_link")],
            [InlineKeyboardButton(text="Инструкция привязки", callback_data="show_link_help")]
        ])

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

async def is_admin_call(call: CallbackQuery) -> bool:
    user = call.from_user
    if not user:
        return False
    user_id = user.id
    if config.get("admin_id") == user_id:
        return True
    if user_id in config.get("allowed_users", []):
        return True
    chat = call.message.chat
    if chat.type in ["group", "supergroup"]:
        try:
            member = await bot.get_chat_member(chat.id, user_id)
            return member.status in ["creator", "administrator"]
        except:
            return False
    return False
    
    return False

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    if not await is_admin(msg):
        return
    
    help_text = """
<b>Forum Relay Bot - Бот-посредник с форумом</b>

<b>Команды для настройки:</b>
/setup - Показать текущие настройки
/set_forum - Установить чат-форум преподавателя (используйте в форуме)
/add_student - Добавить чат ученика (используйте в чате ученика)
/remove_student - Удалить чат ученика (используйте в чате ученика)
/add_admin - Добавить пользователя с правами управления (ответьте на его сообщение)
/remove_admin - Удалить пользователя из списка разрешённых (ответьте на его сообщение)
/help - Показать эту справку

<b>Как работает:</b>
1. Создайте чат-форум в Telegram для преподавателя
2. Добавьте бота в форум и используйте /set_forum
3. Для каждого ученика создайте отдельный чат с ботом
4. В чате ученика используйте /add_student
5. Бот автоматически создаст тему в форуме для этого ученика
6. Все сообщения будут пересылаться между чатом ученика и его темой в форуме

<b>Безопасность:</b>
Только администраторы чатов и разрешённые пользователи могут управлять ботом
Обычные участники НЕ могут использовать команды бота
Первый, кто настроит бота, становится главным администратором
"""
    await answer_safe(msg, help_text, reply_markup=build_main_kb())

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    if not await is_admin(msg):
        return
    await cmd_start(msg)

@dp.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not await is_admin(msg):
        return
    await answer_safe(msg, compose_setup_text(), reply_markup=build_main_kb())

@dp.message(Command("setup"))
async def cmd_setup(msg: Message):
    if not await is_admin(msg):
        return
    status = compose_setup_text()
    await answer_safe(msg, status, reply_markup=build_main_kb())

@dp.callback_query(F.data == "show_setup")
async def cb_show_setup(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    await answer_safe(call.message, compose_setup_text(), reply_markup=build_main_kb())

@dp.callback_query(F.data == "list_students")
async def cb_list_students(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    data = config.get("student_chats", {})
    if not data:
        text = "Список пуст"
    else:
        lines = []
        for cid, info in data.items():
            lines.append(f"Чат {cid}: {info.get('title','')} | Тема {info.get('thread_id')}")
        text = "\n".join(lines)
    await answer_safe(call.message, text, reply_markup=build_students_kb())

@dp.callback_query(F.data == "list_forums")
async def cb_list_forums(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    forums = config.get("forums", [])
    if not forums:
        await call.message.answer("Форумы не настроены")
        return
    rows = []
    for fc in forums:
        title = str(fc)
        try:
            chat_info = await bot.get_chat(int(fc))
            if chat_info and getattr(chat_info, "title", None):
                title = chat_info.title
        except Exception:
            pass
    
        rows.append([InlineKeyboardButton(text=title, callback_data=f"show_forum:{fc}")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="show_setup")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await call.message.answer("Список форумов", reply_markup=kb)

@dp.callback_query(F.data.startswith("show_forum:"))
async def cb_show_forum(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    try:
        forum_chat_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.message.answer("Неверные данные кнопки")
        return
    title = str(forum_chat_id)
    try:
        chat_info = await bot.get_chat(forum_chat_id)
        if chat_info and getattr(chat_info, "title", None):
            title = chat_info.title
    except Exception:
        pass
    
    # Добавляем кнопку отвязки форума
    kb = build_students_kb_for_forum(forum_chat_id)
    # Добавляем кнопку отвязки перед кнопкой "Назад"
    unlink_row = [InlineKeyboardButton(text="🗑 Отвязать форум", callback_data=f"unlink_forum:{forum_chat_id}")]
    kb.inline_keyboard.insert(-1, unlink_row)
    
    await call.message.answer(f"Форум: {title}\nID: <code>{forum_chat_id}</code>", reply_markup=kb)

@dp.callback_query(F.data.startswith("unlink_forum:"))
async def cb_unlink_forum(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    try:
        forum_chat_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.message.answer("Неверные данные кнопки")
        return
    
    forums = config.get("forums", [])
    if forum_chat_id not in forums:
        await call.message.answer("Этот форум уже не привязан")
        return
    
    # Удаляем форум из списка
    forums.remove(forum_chat_id)
    config["forums"] = forums
    
    # Удаляем все привязки учеников к этому форуму
    student_chats = config.get("student_chats", {})
    removed_students = []
    for cid in list(student_chats.keys()):
        if student_chats[cid].get("forum_chat") == forum_chat_id:
            removed_students.append(student_chats[cid].get("title", cid))
            del student_chats[cid]
    config["student_chats"] = student_chats
    save_config(config)
    
    title = str(forum_chat_id)
    try:
        chat_info = await bot.get_chat(forum_chat_id)
        if chat_info and getattr(chat_info, "title", None):
            title = chat_info.title
    except Exception:
        pass
    
    msg_text = f"Форум отвязан: {title}\nID: <code>{forum_chat_id}</code>"
    if removed_students:
        msg_text += f"\n\nУдалено привязок учеников: {len(removed_students)}"
    
    if not forums:
        msg_text += "\n\n⚠️ Форумы не настроены. Используйте /set_forum в нужном форуме."
    
    await call.message.answer(msg_text, reply_markup=build_main_kb())
    log.info(f"Forum unlinked: {forum_chat_id}, removed {len(removed_students)} student bindings")

@dp.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()

@dp.callback_query(F.data == "show_link_help")
async def cb_show_link_help(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    text = """
Привязка чата ученика к теме форума:
1. В чате ученика выполните /add_student
2. В форуме создайте тему и откройте её
3. Скопируйте ID темы из ссылки
4. В чате ученика выполните /link_student ID
"""
    await answer_safe(call.message, text, reply_markup=build_main_kb())

@dp.message(F.forum_topic_created)
async def on_forum_topic_created(msg: Message):
    if msg.chat.id not in config.get("forums", []):
        return
    link = build_topic_link(msg.message_thread_id, msg.chat.id)
    if link:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ссылка темы", callback_data="topic_link_here"), InlineKeyboardButton(text="Сохранить тему", callback_data="save_topic_here")]])
        await bot.send_message(
            msg.chat.id,
            f"Ссылка на тему: {link}\nID темы: <code>{msg.message_thread_id}</code>\nВ чате ученика выполните: /link_student {msg.message_thread_id}",
            message_thread_id=msg.message_thread_id,
            reply_markup=kb
        )

@dp.callback_query(F.data == "save_topic_here")
async def cb_save_topic_here(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    thread_id = call.message.message_thread_id
    pending_links[call.from_user.id] = {"forum_chat": call.message.chat.id, "thread_id": thread_id}
    link = build_topic_link(thread_id, call.message.chat.id)
    await call.message.answer(f"Тема сохранена для привязки. ID: <code>{thread_id}</code>\nСсылка: {link}\nПерейдите в чат ученика и нажмите: Привязать к сохраненной теме")

@dp.message(Command("topic_link"))
async def cmd_topic_link(msg: Message):
    if not await is_admin(msg):
        return
    forums = config.get("forums", [])
    if msg.chat.id not in forums:
        await msg.answer("Эту команду используйте в форуме преподавателя")
        return
    thread_id = None
    args = msg.text.split(maxsplit=1)
    if len(args) > 1:
        raw = args[1].strip()
        m = re.search(r"(\d+)$", raw)
        if m:
            thread_id = int(m.group(1))
    if thread_id is None:
        if msg.message_thread_id:
            thread_id = msg.message_thread_id
        else:
            await msg.answer("Укажите ID темы или выполните команду внутри темы")
            return
    link = build_topic_link(thread_id, msg.chat.id)
    if not link:
        await msg.answer("Не удалось сформировать ссылку")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть", url=link), InlineKeyboardButton(text="Сохранить тему", callback_data="save_topic_here")]]
    )
    await msg.answer(
        f"Ссылка на тему: {link}\nID темы: <code>{thread_id}</code>\nВ чате ученика выполните: /link_student {thread_id}",
        reply_markup=kb
    )

@dp.callback_query(F.data == "topic_link_here")
async def cb_topic_link_here(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    thread_id = call.message.message_thread_id
    link = build_topic_link(thread_id, call.message.chat.id)
    if not link:
        await call.message.answer("Не удалось сформировать ссылку")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть", url=link), InlineKeyboardButton(text="Сохранить тему", callback_data="save_topic_here")]]
    )
    await call.message.answer(
        f"Ссылка на тему: {link}\nID темы: <code>{thread_id}</code>\nВ чате ученика выполните: /link_student {thread_id}",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("send_link:"))
async def cb_send_link(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    try:
        student_chat_id = call.data.split(":", 1)[1]
    except Exception:
        await call.message.answer("Неверные данные кнопки")
        return
    info = config.get("student_chats", {}).get(student_chat_id)
    if not info:
        await call.message.answer("Запись не найдена")
        return
    thread_id = info.get("thread_id")
    forum_chat_id = info.get("forum_chat")
    link = build_topic_link(thread_id, forum_chat_id)
    if not link:
        await call.message.answer("Не удалось сформировать ссылку")
        return
    await bot.send_message(forum_chat_id, f"Ссылка на тему: {link}", message_thread_id=thread_id)
    await call.message.answer(f"Ссылка отправлена в тему\n{link}")

@dp.callback_query(F.data == "link_saved")
async def cb_link_saved(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    pl = pending_links.get(call.from_user.id)
    if not pl or "forum_chat" not in pl or "thread_id" not in pl:
        await call.message.answer("Сначала сохраните тему в форуме: нажмите 'Сохранить тему' внутри нужной темы")
        return
    student_chat_id = str(call.message.chat.id)
    data = config.get("student_chats", {})
    if student_chat_id in data:
        await call.message.answer("Этот чат уже привязан")
        return
    title = call.message.chat.title or f"Ученик {call.message.chat.id}"
    data[student_chat_id] = {"title": title, "forum_chat": pl["forum_chat"], "thread_id": pl["thread_id"]}
    config["student_chats"] = data
    save_config(config)
    link = build_topic_link(pl["thread_id"], pl["forum_chat"])
    await call.message.answer(f"Чат привязан к теме {pl['thread_id']}\n{link}", reply_markup=build_group_kb(call.message.chat.id))
    await bot.send_message(pl["forum_chat"], f"Ссылка на тему: {link}", message_thread_id=pl["thread_id"])
    pending_links.pop(call.from_user.id, None)

@dp.callback_query(F.data.startswith("unlink:"))
async def cb_unlink(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    try:
        chat_id = call.data.split(":", 1)[1]
    except Exception:
        chat_id = str(call.message.chat.id)
    data = config.get("student_chats", {})
    if chat_id in data:
        info = data.pop(chat_id)
        config["student_chats"] = data
        save_config(config)
        if call.message.chat.type == "private":
            await call.message.answer(f"Привязка удалена. Тема была: {info.get('thread_id')}")
        else:
            await call.message.answer(f"Привязка удалена. Тема была: {info.get('thread_id')}", reply_markup=build_group_kb(call.message.chat.id))
    else:
        await call.message.answer("Эта группа не привязана")

@dp.callback_query(F.data == "enter_link")
async def cb_enter_link(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    awaiting_link_input.add(call.message.chat.id)
    await answer_safe(call.message, "Отправьте ID темы или ссылку на тему", reply_markup=build_group_kb(call.message.chat.id))

@dp.message(lambda m: m.chat and m.chat.type in ("group", "supergroup") and m.text and not m.text.startswith("/") and m.chat.id in awaiting_link_input)
async def handle_group_free_text(msg: Message):
    if msg.chat.id not in awaiting_link_input:
        return
    if not await is_admin(msg):
        return
    raw = (msg.text or "").strip()
    m = re.search(r"(\d+)$", raw)
    if not m:
        await answer_safe(msg, "Не удалось распознать ID темы. Отправьте число или ссылку вида t.me/c/<id>/<ID_темы>")
        return
    thread_id = int(m.group(1))
    student_chat_id = str(msg.chat.id)
    data = config.get("student_chats", {})
    if student_chat_id in data:
        await answer_safe(msg, "Этот чат уже привязан", reply_markup=build_group_kb(msg.chat.id))
        awaiting_link_input.discard(msg.chat.id)
        return
    title = msg.chat.title or f"Ученик {msg.chat.id}"
    forums = config.get("forums", [])
    if len(forums) != 1:
        await answer_safe(msg, "Несколько форумов. Укажите ссылку на тему или сохраните тему в нужном форуме и нажмите 'Привязать к сохраненной теме'")
        return
    forum_chat_id = forums[0]
    data[student_chat_id] = {"title": title, "forum_chat": forum_chat_id, "thread_id": thread_id}
    config["student_chats"] = data
    save_config(config)
    link = build_topic_link(thread_id, forum_chat_id)
    await answer_safe(msg, f"Чат привязан к теме {thread_id}\n{link}", reply_markup=build_group_kb(msg.chat.id))
    if forum_chat_id and link:
        await bot.send_message(forum_chat_id, f"Ссылка на тему: {link}", message_thread_id=thread_id)
    awaiting_link_input.discard(msg.chat.id)

@dp.callback_query(F.data.startswith("bind_saved:"))
async def cb_bind_saved(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    pl = pending_links.get(call.from_user.id)
    if not pl or "forum_chat" not in pl or "thread_id" not in pl:
        await call.message.answer("Сначала сохраните тему в форуме: нажмите 'Сохранить тему' внутри нужной темы")
        return
    try:
        target_chat_id = call.data.split(":", 1)[1]
    except Exception:
        await call.message.answer("Неверные данные кнопки")
        return
    data = config.get("student_chats", {})
    if target_chat_id in data:
        await call.message.answer("Этот чат уже привязан")
        return
    title = target_chat_id
    try:
        chat_info = await bot.get_chat(int(target_chat_id))
        if chat_info and getattr(chat_info, "title", None):
            title = chat_info.title
    except Exception:
        pass
    data[target_chat_id] = {"title": title, "forum_chat": pl["forum_chat"], "thread_id": pl["thread_id"]}
    config["student_chats"] = data
    save_config(config)
    link = build_topic_link(pl["thread_id"], pl["forum_chat"])
    await call.message.answer(f"Чат {target_chat_id} привязан к теме {pl['thread_id']}\n{link}")
    await bot.send_message(pl["forum_chat"], f"Ссылка на тему: {link}", message_thread_id=pl["thread_id"])
    pending_links.pop(call.from_user.id, None)

@dp.message(Command("topic_id"))
async def cmd_topic_id(msg: Message):
    if not await is_admin(msg):
        return
    forums = config.get("forums", [])
    if msg.chat.id not in forums:
        await msg.answer("Эту команду используйте в форуме преподавателя")
        return
    thread_id = None
    args = msg.text.split(maxsplit=1)
    if len(args) > 1:
        raw = args[1].strip()
        m = re.search(r"(\d+)$", raw)
        if m:
            thread_id = int(m.group(1))
    if thread_id is None:
        if msg.message_thread_id:
            thread_id = msg.message_thread_id
        else:
            await msg.answer("Укажите ID темы или выполните команду внутри темы")
            return
    await msg.answer(f"ID темы: <code>{thread_id}</code>\nВ чате ученика выполните: /link_student {thread_id}")

@dp.message(Command("set_forum"))
async def cmd_set_forum(msg: Message):
    if not await is_admin(msg):
        await msg.answer("У вас нет прав для выполнения этой команды!")
        return
    
    if msg.chat.type not in ["group", "supergroup"]:
        await msg.answer("Эта команда работает только в групповых чатах!")
        return
    
    chat_info = await bot.get_chat(msg.chat.id)
    if not chat_info.is_forum:
        await msg.answer("Этот чат не является форумом! Включите темы в настройках группы.")
        return
    
    forums = config.get("forums", [])
    if msg.chat.id not in forums:
        forums.append(msg.chat.id)
        config["forums"] = forums
    if not config.get("admin_id"):
        config["admin_id"] = msg.from_user.id
    save_config(config)
    
    await msg.answer(f"Форум добавлен!\nID: <code>{msg.chat.id}</code>\nНазвание: {msg.chat.title}")
    log.info(f"Forum added: {msg.chat.id} ({msg.chat.title})")

@dp.message(Command("add_student"))
async def cmd_add_student(msg: Message):
    if not await is_admin(msg):
        await msg.answer("У вас нет прав для выполнения этой команды!")
        return
    
    if msg.chat.type not in ["group", "supergroup"]:
        await msg.answer("Эта команда работает только в групповых чатах!")
        return
    
    forums = config.get("forums", [])
    if not forums:
        await msg.answer("Сначала установите форум преподавателя командой /set_forum!")
        return
    
    student_chat_id = str(msg.chat.id)
    student_chats = config.get("student_chats", {})
    
    if student_chat_id in student_chats:
        await msg.answer(f"Этот чат уже добавлен! ID темы: {student_chats[student_chat_id]['thread_id']}")
        return
    
    topic_name = msg.chat.title or f"Ученик {msg.chat.id}"
    
    help_text = f"""
Не удалось автоматически создать тему в форуме.

Сделайте вручную:
1. Откройте форум преподавателя
2. Создайте новую тему с названием: {topic_name}
3. Откройте созданную тему
4. Скопируйте ID темы из URL (число после /?)
5. В этом чате отправьте: /link_student ID_темы

Пример: /link_student 123456
"""
    await msg.answer(help_text)
    await msg.answer("Панель привязки:", reply_markup=build_group_kb(msg.chat.id))
    log.info(f"Manual topic creation required for: {student_chat_id}")

@dp.message(Command("link_student"))
async def cmd_link_student(msg: Message):
    if not await is_admin(msg):
        await msg.answer("У вас нет прав для выполнения этой команды!")
        return
    
    if msg.chat.type not in ["group", "supergroup"]:
        await msg.answer("Эта команда работает только в групповых чатах!")
        return
    
    args = msg.text.split(maxsplit=1)
    raw_input = args[1].strip() if len(args) > 1 else None

    forums = config.get("forums", [])
    if msg.chat.id in forums:
        thread_id = None
        if raw_input:
            m_forum = re.search(r"(\d+)$", raw_input)
            if m_forum:
                thread_id = int(m_forum.group(1))
        if thread_id is None and msg.message_thread_id:
            thread_id = msg.message_thread_id
        if thread_id is None:
            await answer_safe(
                msg,
                "Укажите ID темы или выполните команду внутри нужной темы"
            )
            return
        link = build_topic_link(thread_id, msg.chat.id)
        text = f"Тема: <code>{thread_id}</code>\nСсылка на тему: {link}\nВ чате ученика выполните: /link_student {thread_id}"
        await answer_safe(msg, text)
        return

    if not raw_input:
        await msg.answer("Использование: /link_student ID_темы ИЛИ ссылка на тему\nПримеры:\n/link_student 123456\n/link_student https://t.me/c/3295305247/123456")
        return

    thread_id = None
    forum_chat_id = None
    m_link = re.search(r"t\.me/c/(\d+)/(\d+)", raw_input)
    if m_link:
        internal = int(m_link.group(1))
        thread_id = int(m_link.group(2))
        for fc in forums:
            cid = abs(int(fc))
            internal_num = cid - 1000000000000 if cid > 1000000000000 else cid
            if internal_num == internal:
                forum_chat_id = fc
                break
        if forum_chat_id is None:
            await msg.answer("Эта ссылка не относится к известным форумам. Сначала добавьте форум командой /set_forum в нужном форуме")
            return
    else:
        m = re.search(r"(\d+)$", raw_input)
        if not m:
            await msg.answer("Не удалось распознать ID темы. Укажите число или ссылку вида t.me/c/<id>/<ID_темы>")
            return
        thread_id = int(m.group(1))
        if len(forums) == 1:
            forum_chat_id = forums[0]
        else:
            await msg.answer("Несколько форумов. Укажите ссылку на тему из нужного форума или сохраните тему в форуме и нажмите 'Привязать к сохраненной теме'")
            return
    
    student_chat_id = str(msg.chat.id)
    student_chats = config.get("student_chats", {})
    
    if student_chat_id in student_chats:
        await msg.answer(f"Этот чат уже привязан к теме {student_chats[student_chat_id]['thread_id']}")
        return
    
    topic_name = msg.chat.title or f"Ученик {msg.chat.id}"
    
    student_chats[student_chat_id] = {
        "title": topic_name,
        "forum_chat": forum_chat_id,
        "thread_id": thread_id
    }
    config["student_chats"] = student_chats
    save_config(config)
    
    await msg.answer(f"Чат ученика привязан к теме {thread_id}!")
    link = build_topic_link(thread_id, forum_chat_id)
    if link:
        await bot.send_message(forum_chat_id, f"Ссылка на тему: {link}", message_thread_id=thread_id)
    log.info(f"Student chat linked: {student_chat_id} -> thread {thread_id}")
    awaiting_link_input.discard(msg.chat.id)

@dp.message(Command("remove_student"))
async def cmd_remove_student(msg: Message):
    if not await is_admin(msg):
        await msg.answer("У вас нет прав для выполнения этой команды!")
        return
    
    student_chat_id = str(msg.chat.id)
    student_chats = config.get("student_chats", {})
    
    if student_chat_id not in student_chats:
        await msg.answer("Этот чат не добавлен в список учеников!")
        return
    
    student_info = student_chats[student_chat_id]
    del student_chats[student_chat_id]
    config["student_chats"] = student_chats
    save_config(config)
    
    await msg.answer(f"Чат ученика удалён из списка!\nТема в форуме: {student_info['thread_id']}")
    log.info(f"Student chat removed: {student_chat_id}")

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

def contains_nickname(text: str) -> bool:
    return bool(get_nickname_warning(text))

def get_nickname_warning(text: str) -> str:
    if not text:
        return ""

    # 1. Ссылки (http, https, t.me, и т.д.)
    if re.search(r'https?://|t\.me/|www\.|\.ru/|\.com/|\.org/', text, re.IGNORECASE):
        return "[Сообщение содержит ссылку]"

    # 2. Явный никнейм с @ (например @username)
    for match in re.finditer(r'@([A-Za-z0-9_]{3,})', text):
        username = match.group(1)
        if not is_allowed_username(username):
            return "[Сообщение содержит никнейм]"

    # 3. Email
    if EMAIL_PATTERN.search(text):
        return "[Сообщение содержит email]"

    # 4. Номер телефона (по количеству цифр в похожем шаблоне)
    if has_phone_number(text):
        return "[Сообщение содержит номер телефона]"

    return ""
async def forward_to_forum(msg: Message, forum_chat_id: int, thread_id: int, student_name: str):
    try:
        sender_name = format_user_name(msg.from_user, "Неизвестно")
        header = f"<b>{sender_name}:</b>\n\n"
        
        # Проверка текста на контакты/ник/телефон/латиницу
        text_to_check = msg.text or msg.caption or ""
        warning = get_nickname_warning(text_to_check)
        if warning:
            await bot.send_message(forum_chat_id, header + warning, message_thread_id=thread_id)
            log.info(f"Message with sensitive data filtered from student {student_name}")
            return True
        
        if msg.text:
            # Разбиваем большие сообщения на части
            full_text = header + msg.text
            if len(full_text) <= MAX_MESSAGE_LENGTH:
                await bot.send_message(forum_chat_id, full_text, message_thread_id=thread_id)
            else:
                # Отправляем заголовок отдельно, потом текст частями
                await bot.send_message(forum_chat_id, header.strip(), message_thread_id=thread_id)
                text = msg.text
                while text:
                    chunk = text[:MAX_MESSAGE_LENGTH]
                    text = text[MAX_MESSAGE_LENGTH:]
                    await bot.send_message(forum_chat_id, chunk, message_thread_id=thread_id)
        elif msg.photo:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_photo(forum_chat_id, msg.photo[-1].file_id, caption=header.strip(), message_thread_id=thread_id)
                await bot.send_message(forum_chat_id, msg.caption, message_thread_id=thread_id)
            else:
                await bot.send_photo(forum_chat_id, msg.photo[-1].file_id, caption=caption, message_thread_id=thread_id)
        elif msg.video:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_video(forum_chat_id, msg.video.file_id, caption=header.strip(), message_thread_id=thread_id)
                await bot.send_message(forum_chat_id, msg.caption, message_thread_id=thread_id)
            else:
                await bot.send_video(forum_chat_id, msg.video.file_id, caption=caption, message_thread_id=thread_id)
        elif msg.document:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_document(forum_chat_id, msg.document.file_id, caption=header.strip(), message_thread_id=thread_id)
                await bot.send_message(forum_chat_id, msg.caption, message_thread_id=thread_id)
            else:
                await bot.send_document(forum_chat_id, msg.document.file_id, caption=caption, message_thread_id=thread_id)
        elif msg.voice:
            await bot.send_voice(forum_chat_id, msg.voice.file_id, caption=header.strip(), message_thread_id=thread_id)
        elif msg.audio:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_audio(forum_chat_id, msg.audio.file_id, caption=header.strip(), message_thread_id=thread_id)
                await bot.send_message(forum_chat_id, msg.caption, message_thread_id=thread_id)
            else:
                await bot.send_audio(forum_chat_id, msg.audio.file_id, caption=caption, message_thread_id=thread_id)
        elif msg.video_note:
            await bot.send_video_note(forum_chat_id, msg.video_note.file_id, message_thread_id=thread_id)
            await bot.send_message(forum_chat_id, header + "Видеосообщение", message_thread_id=thread_id)
        elif msg.sticker:
            await bot.send_sticker(forum_chat_id, msg.sticker.file_id, message_thread_id=thread_id)
            await bot.send_message(forum_chat_id, header + "Стикер", message_thread_id=thread_id)
        else:
            await bot.send_message(forum_chat_id, header + "[Неподдерживаемый тип сообщения]", message_thread_id=thread_id)
        
        log.info(f"Message forwarded from student {student_name} to forum {forum_chat_id} thread {thread_id}")
        return True
    except Exception as e:
        log.error(f"Error forwarding to forum: {e}")
        return False

async def forward_to_student(msg: Message, student_chat_id: int):
    try:
        sender_name = format_user_name(msg.from_user, "Преподаватель")
        header = f"<b>{sender_name}:</b>\n\n"
        # Проверка текста на контакты/ник/телефон/латиницу
        text_to_check = msg.text or msg.caption or ""
        warning = get_nickname_warning(text_to_check)
        if warning:
            await bot.send_message(student_chat_id, header + warning)
            log.info(f"Message with sensitive data filtered to student {student_chat_id}")
            return True
        
        if msg.text:
            # Разбиваем большие сообщения на части
            full_text = header + msg.text
            if len(full_text) <= MAX_MESSAGE_LENGTH:
                await bot.send_message(student_chat_id, full_text)
            else:
                await bot.send_message(student_chat_id, header.strip())
                text = msg.text
                while text:
                    chunk = text[:MAX_MESSAGE_LENGTH]
                    text = text[MAX_MESSAGE_LENGTH:]
                    await bot.send_message(student_chat_id, chunk)
        elif msg.photo:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_photo(student_chat_id, msg.photo[-1].file_id, caption=header.strip())
                await bot.send_message(student_chat_id, msg.caption)
            else:
                await bot.send_photo(student_chat_id, msg.photo[-1].file_id, caption=caption)
        elif msg.video:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_video(student_chat_id, msg.video.file_id, caption=header.strip())
                await bot.send_message(student_chat_id, msg.caption)
            else:
                await bot.send_video(student_chat_id, msg.video.file_id, caption=caption)
        elif msg.document:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_document(student_chat_id, msg.document.file_id, caption=header.strip())
                await bot.send_message(student_chat_id, msg.caption)
            else:
                await bot.send_document(student_chat_id, msg.document.file_id, caption=caption)
        elif msg.voice:
            await bot.send_voice(student_chat_id, msg.voice.file_id, caption=header.strip())
        elif msg.audio:
            caption = header + (msg.caption or "")
            if len(caption) > 1024:
                await bot.send_audio(student_chat_id, msg.audio.file_id, caption=header.strip())
                await bot.send_message(student_chat_id, msg.caption)
            else:
                await bot.send_audio(student_chat_id, msg.audio.file_id, caption=caption)
        elif msg.video_note:
            await bot.send_video_note(student_chat_id, msg.video_note.file_id)
            await bot.send_message(student_chat_id, header + "Видеосообщение")
        elif msg.sticker:
            await bot.send_sticker(student_chat_id, msg.sticker.file_id)
            await bot.send_message(student_chat_id, header + "Стикер")
        else:
            await bot.send_message(student_chat_id, header + "[Неподдерживаемый тип сообщения]")
        
        log.info(f"Message forwarded from forum to student {student_chat_id}")
        return True
    except Exception as e:
        error_str = str(e)
        # Обработка миграции чата
        if "migrated" in error_str.lower() or "upgraded to a supergroup" in error_str.lower():
            match = re.search(r'id[:\s]+(-?\d+)', error_str)
            if match:
                new_id = match.group(1)
                old_id = str(student_chat_id)
                student_chats = config.get("student_chats", {})
                if old_id in student_chats:
                    student_chats[new_id] = student_chats.pop(old_id)
                    config["student_chats"] = student_chats
                    save_config(config)
                    log.info(f"Auto-migrated chat: {old_id} -> {new_id}")
                    # Повторяем отправку на новый ID
                    return await forward_to_student(msg, int(new_id))
        log.error(f"Error forwarding to student: {e}")
        return False

async def forward_media_group_to_forum(messages: list, forum_chat_id: int, thread_id: int, student_name: str):
    """Пересылает медиагруппу (несколько файлов) в форум"""
    try:
        if not messages:
            return False
        
        first_msg = messages[0]
        sender_name = format_user_name(first_msg.from_user, "Неизвестно")
        header = f"<b>{sender_name}:</b>"
        
        # Проверяем caption на контакты
        caption_text = ""
        for m in messages:
            if m.caption:
                caption_text = m.caption
                break
        
        warning = get_nickname_warning(caption_text)
        if warning:
            await bot.send_message(forum_chat_id, header + "\n\n" + warning, message_thread_id=thread_id)
            return True
        
        # Собираем медиагруппу
        media = []
        for i, m in enumerate(messages):
            cap = header if i == 0 else None
            if m.photo:
                media.append(InputMediaPhoto(media=m.photo[-1].file_id, caption=cap, parse_mode="HTML"))
            elif m.video:
                media.append(InputMediaVideo(media=m.video.file_id, caption=cap, parse_mode="HTML"))
            elif m.document:
                media.append(InputMediaDocument(media=m.document.file_id, caption=cap, parse_mode="HTML"))
            elif m.audio:
                media.append(InputMediaAudio(media=m.audio.file_id, caption=cap, parse_mode="HTML"))
        
        if media:
            await bot.send_media_group(forum_chat_id, media, message_thread_id=thread_id)
            # Отправляем caption отдельно если есть
            if caption_text:
                await bot.send_message(forum_chat_id, caption_text, message_thread_id=thread_id)
            log.info(f"Media group ({len(media)} items) forwarded from student {student_name}")
        return True
    except Exception as e:
        log.error(f"Error forwarding media group to forum: {e}")
        return False

async def forward_media_group_to_student(messages: list, student_chat_id: int):
    """Пересылает медиагруппу (несколько файлов) ученику"""
    try:
        if not messages:
            return False
        
        first_msg = messages[0]
        sender_name = format_user_name(first_msg.from_user, "Преподаватель")
        header = f"<b>{sender_name}:</b>"
        
        # Проверяем caption на контакты
        caption_text = ""
        for m in messages:
            if m.caption:
                caption_text = m.caption
                break
        
        warning = get_nickname_warning(caption_text)
        if warning:
            await bot.send_message(student_chat_id, header + "\n\n" + warning)
            return True
        
        # Собираем медиагруппу
        media = []
        for i, m in enumerate(messages):
            cap = header if i == 0 else None
            if m.photo:
                media.append(InputMediaPhoto(media=m.photo[-1].file_id, caption=cap, parse_mode="HTML"))
            elif m.video:
                media.append(InputMediaVideo(media=m.video.file_id, caption=cap, parse_mode="HTML"))
            elif m.document:
                media.append(InputMediaDocument(media=m.document.file_id, caption=cap, parse_mode="HTML"))
            elif m.audio:
                media.append(InputMediaAudio(media=m.audio.file_id, caption=cap, parse_mode="HTML"))
        
        if media:
            await bot.send_media_group(student_chat_id, media)
            if caption_text:
                await bot.send_message(student_chat_id, caption_text)
            log.info(f"Media group ({len(media)} items) forwarded to student {student_chat_id}")
        return True
    except Exception as e:
        log.error(f"Error forwarding media group to student: {e}")
        return False

async def process_media_group(media_group_id: str, direction: str, target_id: int, thread_id: int = None, student_name: str = None):
    """Обрабатывает накопленную медиагруппу"""
    messages = media_group_buffer.pop(media_group_id, [])
    if media_group_id in media_group_timers:
        del media_group_timers[media_group_id]
    
    if not messages:
        return
    
    if direction == "to_forum":
        await forward_media_group_to_forum(messages, target_id, thread_id, student_name)
    else:
        await forward_media_group_to_student(messages, target_id)

@dp.callback_query(F.data == "names_menu")
async def cb_names_menu(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    forums = config.get("forums", [])
    if not forums:
        await call.message.answer("Форумы не настроены")
        return
    rows = []
    for fc in forums:
        title = str(fc)
        try:
            chat_info = await bot.get_chat(int(fc))
            if chat_info and getattr(chat_info, "title", None):
                title = chat_info.title
        except Exception:
            pass
        rows.append([InlineKeyboardButton(text=title, callback_data=f"names_forum:{fc}")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="show_setup")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await call.message.answer("Выберите форум для настройки имён", reply_markup=kb)

@dp.callback_query(F.data.startswith("names_forum:"))
async def cb_names_forum(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    try:
        forum_chat_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.message.answer("Неверные данные кнопки")
        return
    students = []
    for cid, info in config.get("student_chats", {}).items():
        if info.get("forum_chat") == forum_chat_id:
            title = info.get("title", cid)
            students.append((cid, title))
    rows = []
    rows.append([InlineKeyboardButton(text="Участники форума", callback_data=f"names_student:{forum_chat_id}")])
    for cid, title in students:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"names_student:{cid}")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="names_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    text = "Выберите чат ученика или участников форума"
    if not students:
        await call.message.answer("Для этого форума нет привязанных чатов учеников")
    await call.message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("names_student:"))
async def cb_names_student(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    chat_id = call.data.split(":", 1)[1]
    participants = config.get("participants", {}).get(chat_id, {})
    if not participants:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить участника", callback_data=f"add_participant:{chat_id}")],
            [InlineKeyboardButton(text="Назад", callback_data="names_menu")]
        ])
        await call.message.answer("Нет сохранённых участников. Добавьте вручную или подождите, пока кто-то напишет.", reply_markup=kb)
        return
    rows = []
    for uid, info in participants.items():
        base_name = info.get("name", uid)
        alias = config.get("aliases", {}).get(uid)
        text = base_name
        if alias:
            text = f"{base_name} → {alias}"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"names_user:{chat_id}:{uid}")])
    rows.append([InlineKeyboardButton(text="Добавить участника", callback_data=f"add_participant:{chat_id}")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="names_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await call.message.answer("Выберите участника для переименования", reply_markup=kb)

@dp.callback_query(F.data.startswith("names_user:"))
async def cb_names_user(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    try:
        _, chat_id, user_id = call.data.split(":", 2)
    except Exception:
        await call.message.answer("Неверные данные кнопки")
        return
    participants = config.get("participants", {}).get(chat_id, {})
    info = participants.get(user_id, {})
    base_name = info.get("name", user_id)
    alias = config.get("aliases", {}).get(user_id)
    pending_alias[call.from_user.id] = {"user_id": user_id}
    text = f"Текущее имя: {base_name}"
    if alias:
        text += f"\nТекущий псевдоним: {alias}"
    text += "\nОтправьте новое имя в личные сообщения боту. Чтобы сбросить псевдоним, отправьте знак -"
    await call.message.answer(text)

@dp.callback_query(F.data.startswith("add_participant:"))
async def cb_add_participant(call: CallbackQuery):
    if not await is_admin_call(call):
        await call.answer("Нет прав", show_alert=True)
        return
    await call.answer()
    chat_id = call.data.split(":", 1)[1]
    pending_add_participant[call.from_user.id] = {"chat_id": chat_id, "step": "user_id"}
    await call.message.answer("Перешлите сюда сообщение от нужного участника ИЛИ отправьте его user_id числом.")

@dp.message(F.chat.type == "private")
async def handle_private_input(msg: Message):
    if not await is_admin(msg):
        return
    raw = (msg.text or "").strip()
    
    add_state = pending_add_participant.get(msg.from_user.id)
    if add_state:
        step = add_state.get("step")
        chat_id = add_state.get("chat_id")
        if step == "user_id":
            if msg.forward_from:
                user = msg.forward_from
                add_state["user_id"] = str(user.id)
                add_state["step"] = "name"
                await msg.answer("Теперь отправьте имя участника (например: ученик Иван)")
                return
            if not raw.lstrip("-").isdigit():
                await msg.answer("Ошибка: user_id должен быть числом")
                return
            add_state["user_id"] = raw
            add_state["step"] = "name"
            await msg.answer("Теперь отправьте имя участника (например: ученик Иван)")
            return
        elif step == "name":
            user_id = add_state.get("user_id")
            participants = config.get("participants", {})
            chat_part = participants.get(chat_id, {})
            chat_part[user_id] = {"name": raw}
            participants[chat_id] = chat_part
            config["participants"] = participants
            aliases = config.get("aliases", {})
            aliases[user_id] = raw
            config["aliases"] = aliases
            save_config(config)
            pending_add_participant.pop(msg.from_user.id, None)
            await msg.answer(f"Участник добавлен: {raw}")
            return
    
    alias_state = pending_alias.get(msg.from_user.id)
    if alias_state:
        user_id = alias_state.get("user_id")
        aliases = config.get("aliases", {})
        if raw == "-":
            if user_id in aliases:
                aliases.pop(user_id)
        elif raw:
            aliases[user_id] = raw
        config["aliases"] = aliases
        save_config(config)
        pending_alias.pop(msg.from_user.id, None)
        await msg.answer("Имя обновлено")
        return

@dp.callback_query(F.data == "admin_menu")
async def cb_admin_menu(call: CallbackQuery):
    """Меню управления администраторами"""
    if call.from_user.id != config.get("admin_id"):
        await call.answer("Только главный администратор может управлять списком админов", show_alert=True)
        return
    await call.answer()
    
    admin_id = config.get("admin_id")
    allowed_users = config.get("allowed_users", [])
    
    text = f"<b>Управление администраторами</b>\n\n"
    text += f"Главный админ: <code>{admin_id}</code>\n\n"
    
    if allowed_users:
        text += "<b>Разрешённые пользователи:</b>\n"
        for uid in allowed_users:
            alias = config.get("aliases", {}).get(str(uid), f"ID {uid}")
            text += f"• {alias} (<code>{uid}</code>)\n"
    else:
        text += "Нет дополнительных администраторов\n"
    
    text += "\n<b>Как добавить администратора:</b>\n"
    text += "1. Попросите пользователя написать любое сообщение в чат с ботом или в группу\n"
    text += "2. Ответьте на его сообщение командой /add_admin\n\n"
    text += "<b>Как удалить администратора:</b>\n"
    text += "Ответьте на сообщение пользователя командой /remove_admin"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="show_setup")]
    ])
    
    await call.message.answer(text, reply_markup=kb)

@dp.my_chat_member()
async def on_my_chat_member(update: ChatMemberUpdated):
    chat = update.chat
    if chat.type not in ["group", "supergroup"]:
        return
    new_status = getattr(update.new_chat_member, "status", None)
    old_status = getattr(update.old_chat_member, "status", None)
    if new_status in ("member", "administrator", "creator") and old_status in ("left", "kicked", None):
        actor_id = update.from_user.id if update.from_user else None
        allowed = set(config.get("allowed_users", []))
        if config.get("admin_id"):
            allowed.add(config.get("admin_id"))
        if actor_id is None or actor_id not in allowed:
            try:
                await bot.leave_chat(chat.id)
            except Exception:
                pass

@dp.message(F.migrate_to_chat_id)
async def on_chat_migration(msg: Message):
    """Обработка миграции группы в супергруппу"""
    old_id = str(msg.chat.id)
    new_id = str(msg.migrate_to_chat_id)
    
    student_chats = config.get("student_chats", {})
    if old_id in student_chats:
        # Переносим привязку на новый ID
        student_chats[new_id] = student_chats.pop(old_id)
        config["student_chats"] = student_chats
        save_config(config)
        log.info(f"Chat migrated: {old_id} -> {new_id}")

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(msg: Message):
    update_participant(msg.chat.id, msg.from_user)
    student_chats = config.get("student_chats", {})
    forums = config.get("forums", [])
    
    if not forums:
        return
    
    if msg.text and msg.text.startswith('/'):
        return
    
    if msg.chat.id in awaiting_link_input:
        return
    
    chat_id_str = str(msg.chat.id)
    
    # Обработка медиагрупп (несколько файлов)
    if msg.media_group_id:
        media_group_buffer[msg.media_group_id].append(msg)
        
        # Определяем направление и параметры
        if msg.chat.id in forums:
            if msg.message_thread_id:
                for student_chat_id, info in student_chats.items():
                    if info.get("forum_chat") == msg.chat.id and info["thread_id"] == msg.message_thread_id:
                        # Отменяем предыдущий таймер если есть
                        if msg.media_group_id in media_group_timers:
                            media_group_timers[msg.media_group_id].cancel()
                        # Запускаем новый таймер
                        timer = asyncio.create_task(
                            asyncio.sleep(0.5)
                        )
                        media_group_timers[msg.media_group_id] = timer
                        try:
                            await timer
                            await process_media_group(msg.media_group_id, "to_student", int(student_chat_id))
                        except asyncio.CancelledError:
                            pass
                        break
        elif chat_id_str in student_chats:
            info = student_chats[chat_id_str]
            thread_id = info["thread_id"]
            forum_chat_id = info.get("forum_chat")
            student_name = info["title"]
            if forum_chat_id:
                if msg.media_group_id in media_group_timers:
                    media_group_timers[msg.media_group_id].cancel()
                timer = asyncio.create_task(
                    asyncio.sleep(0.5)
                )
                media_group_timers[msg.media_group_id] = timer
                try:
                    await timer
                    await process_media_group(msg.media_group_id, "to_forum", forum_chat_id, thread_id, student_name)
                except asyncio.CancelledError:
                    pass
        return
    
    # Обычные сообщения (не медиагруппы)
    if msg.chat.id in forums:
        if msg.message_thread_id:
            for student_chat_id, info in list(student_chats.items()):
                if info.get("forum_chat") == msg.chat.id and info["thread_id"] == msg.message_thread_id:
                    await forward_to_student(msg, int(student_chat_id))
                    break
    
    elif chat_id_str in student_chats:
        info = student_chats[chat_id_str]
        thread_id = info["thread_id"]
        forum_chat_id = info.get("forum_chat")
        student_name = info["title"]
        if forum_chat_id:
            await forward_to_forum(msg, forum_chat_id, thread_id, student_name)

async def main():
    log.info("Forum Relay Bot zapushen!")
    log.info(f"Forums: {config.get('forums', [])}")
    log.info(f"Student chats: {len(config.get('student_chats', {}))}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
