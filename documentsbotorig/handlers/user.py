from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from config import ALLOWED_IDS
from utils.state import get_nested_value, set_nested_value
from utils.validators import validate_field
from utils.file_utils import generate_files, load_templates
from keyboards import templates_kb, confirm_kb, table_row_kb, select_kb, bool_kb
import json

router = Router()
user_states = {}

@router.message(Command("start"))
async def start_handler(message: types.Message):
    if message.from_user.id not in ALLOWED_IDS:
        await message.answer("🚫 У вас нет доступа к боту")
        return

    kb = templates_kb(load_templates())
    await message.reply("📄 Выберите шаблон:", reply_markup=kb)

@router.callback_query(F.data.startswith("template:"))
async def template_select_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in ALLOWED_IDS:
        await callback.answer("🚫 Нет доступа", show_alert=True)
        return

    slug = callback.data.split(":")[1]
    user_states[callback.from_user.id] = {
        "template": slug,
        "fields": {},
        "step": 0,
        "array": None,  # прогресс заполнения массива (таблицы)
    }
    await ask_next_field(callback.from_user.id, callback.message)
    await callback.answer()

async def ask_next_field(user_id, message):
    state = user_states[user_id]
    slug = state["template"]

    import json
    with open(f"templates/{slug}/fields.json", "r", encoding="utf-8") as f:
        template = json.load(f)
    fields = template["fields"]

    if state["step"] >= len(fields):
        preview = "\n".join([f"{f['label']}: {get_nested_value(state['fields'], f['key'])}" for f in fields])
        await message.answer(f"Предпросмотр:\n{preview}", reply_markup=confirm_kb())
        return

    f = fields[state["step"]]
    # обработка массива (табличных строк)
    if f.get("type") == "array":
        items = f.get("items") or f.get("item_fields")
        if not items or not isinstance(items, list):
            await message.answer("⚠️ Ошибка конфигурации: для array требуется items[]")
            state["step"] += 1
            await ask_next_field(user_id, message)
            return
        # инициализируем прогресс массива, если ещё нет
        if not state.get("array") or state["array"].get("field_key") != f["key"]:
            state["array"] = {
                "field_key": f["key"],
                "items": items,
                "rows": [],
                "row_index": 0,
                "col_index": 0,
            }
        arr = state["array"]
        col = arr["items"][arr["col_index"]]
        prompt = f"{f['label']} → Строка {arr['row_index'] + 1}. {col['label']} (пример: {col.get('placeholder','')})"
        # Поддержка select/bool внутри массивов
        if col.get("type") == "select" and isinstance(col.get("options"), list) and col.get("options"):
            await message.answer(prompt, reply_markup=select_kb(col["options"]))
            return
        if col.get("type") == "bool":
            await message.answer(prompt, reply_markup=bool_kb())
            return
        await message.answer(prompt)
        return

    # обычное поле
    required_mark = " (обязательно)" if f.get("required") else ""
    prompt = f"{f['label']}{required_mark} (пример: {f.get('placeholder','')})"
    if f.get("type") == "select" and isinstance(f.get("options"), list) and f.get("options"):
        await message.answer(prompt, reply_markup=select_kb(f["options"]))
        return
    if f.get("type") == "bool":
        await message.answer(prompt, reply_markup=bool_kb())
        return
    await message.answer(prompt)

@router.message()
async def handle_answer(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return

    state = user_states[user_id]
    slug = state["template"]

    with open(f"templates/{slug}/fields.json", "r", encoding="utf-8") as f:
        template = json.load(f)

    fields = template["fields"]

    # если все поля уже пройдены
    if state["step"] >= len(fields):
        await ask_next_field(user_id, message)
        return

    f = fields[state["step"]]

    # если сейчас заполняется массив
    if state.get("array") and state["array"].get("field_key") == f["key"]:
        arr = state["array"]
        items = arr["items"]
        col = items[arr["col_index"]]
        text = (message.text or "").strip()
        # Особая обработка select/bool как текстовый ввод (fallback)
        if col.get("type") == "select" and isinstance(col.get("options"), list) and col.get("options"):
            if text in col["options"]:
                if arr.get("current_row") is None:
                    arr["current_row"] = {}
                arr["current_row"][col["key"]] = text
                arr["col_index"] += 1
            else:
                await message.reply("Пожалуйста, выберите вариант с кнопок.")
                return
        elif col.get("type") == "bool":
            t = text.lower()
            if t in {"да","yes","y","true","1","д"}:
                val = "Да"
            elif t in {"нет","no","n","false","0","н"}:
                val = "Нет"
            else:
                await message.reply("Пожалуйста, выберите 'Да' или 'Нет' с кнопок.")
                return
            if arr.get("current_row") is None:
                arr["current_row"] = {}
            arr["current_row"][col["key"]] = val
            arr["col_index"] += 1
        else:
            # валидация текущего поля строки
            if not validate_field(text, col.get("type", "string")):
                await message.reply("⚠️ Неверный формат, попробуйте снова.")
                return
            # временно сохраняем в текущую строку
            if arr.get("current_row") is None:
                arr["current_row"] = {}
            arr["current_row"][col["key"]] = text
            arr["col_index"] += 1

        # если строка закончилась → показать клавиатуру добавить/готово
        if arr["col_index"] >= len(items):
            # завершили строку, ждём решения пользователя
            await message.answer("Строка заполнена. Добавить ещё строку?", reply_markup=table_row_kb())
            return
        else:
            # спрашиваем следующий столбец
            next_col = items[arr["col_index"]]
            prompt = f"{f['label']} → Строка {arr['row_index'] + 1}. {next_col['label']} (пример: {next_col.get('placeholder','')})"
            if next_col.get("type") == "select" and isinstance(next_col.get("options"), list) and next_col.get("options"):
                await message.answer(prompt, reply_markup=select_kb(next_col["options"]))
                return
            if next_col.get("type") == "bool":
                await message.answer(prompt, reply_markup=bool_kb())
                return
            await message.answer(prompt)
            return

    # обработка обычного поля (required/select/bool)
    text = (message.text or "").strip()
    if f.get("required") and not text:
        await message.reply("⚠️ Это поле обязательно. Введите значение.")
        return

    if f.get("type") == "select" and isinstance(f.get("options"), list) and f.get("options"):
        if text not in f["options"]:
            await message.reply("Пожалуйста, выберите вариант с кнопок.")
            return
        set_nested_value(state["fields"], f["key"], text)
    elif f.get("type") == "bool":
        t = text.lower()
        if t in {"да","yes","y","true","1","д"}:
            val = "Да"
        elif t in {"нет","no","n","false","0","н"}:
            val = "Нет"
        else:
            await message.reply("Пожалуйста, выберите 'Да' или 'Нет' с кнопок.")
            return
        set_nested_value(state["fields"], f["key"], val)
    else:
        if not validate_field(text, f["type"]):
            await message.reply("⚠️ Неверный формат, попробуйте снова.")
            return
        set_nested_value(state["fields"], f["key"], text)

    state["step"] += 1
    await ask_next_field(user_id, message)


@router.callback_query(F.data == "confirm")
async def confirm_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_states or user_id not in ALLOWED_IDS:
        await callback.answer("🚫 Нет доступа", show_alert=True)
        return

    state = user_states[user_id]
    docx_path, pdf_path = generate_files(state["template"], state["fields"])

    # Понятные имена файлов при отправке
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    slug = state["template"]
    docx_name = f"{slug}_{ts}.docx"
    pdf_name = f"{slug}_{ts}.pdf"

    await callback.message.answer_document(FSInputFile(docx_path, filename=docx_name))
    if pdf_path and isinstance(pdf_path, str):
        await callback.message.answer_document(FSInputFile(pdf_path, filename=pdf_name))

    import os
    os.remove(docx_path)
    if pdf_path and os.path.exists(pdf_path):
        os.remove(pdf_path)

    await callback.message.answer("✅ Файлы сгенерированы и отправлены.")
    del user_states[user_id]


@router.callback_query(F.data.startswith("opt:"))
async def select_option(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_states or user_id not in ALLOWED_IDS:
        await callback.answer("🚫 Нет доступа", show_alert=True)
        return

    state = user_states[user_id]
    slug = state["template"]
    with open(f"templates/{slug}/fields.json", "r", encoding="utf-8") as f:
        template = json.load(f)
    fields = template["fields"]
    if state["step"] >= len(fields):
        await callback.answer()
        return
    f = fields[state["step"]]

    # Индекс выбранной опции
    try:
        idx = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer()
        return

    # Массив (таблица) в процессе?
    if state.get("array") and state["array"].get("field_key") == f.get("key"):
        arr = state["array"]
        items = arr["items"]
        col = items[arr["col_index"]]
        options = col.get("options") or []
        if not isinstance(options, list) or idx < 0 or idx >= len(options):
            await callback.answer("Некорректный выбор", show_alert=True)
            return
        value = options[idx]
        if arr.get("current_row") is None:
            arr["current_row"] = {}
        arr["current_row"][col["key"]] = value
        arr["col_index"] += 1
        # переход дальше
        if arr["col_index"] >= len(items):
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Строка заполнена. Добавить ещё строку?", reply_markup=table_row_kb())
            await callback.answer("Выбрано")
            return
        next_col = items[arr["col_index"]]
        prompt = f"{f['label']} → Строка {arr['row_index'] + 1}. {next_col['label']} (пример: {next_col.get('placeholder','')})"
        await callback.message.edit_reply_markup(reply_markup=None)
        if next_col.get("type") == "select" and isinstance(next_col.get("options"), list) and next_col.get("options"):
            await callback.message.answer(prompt, reply_markup=select_kb(next_col["options"]))
        elif next_col.get("type") == "bool":
            await callback.message.answer(prompt, reply_markup=bool_kb())
        else:
            await callback.message.answer(prompt)
        await callback.answer("Выбрано")
        return

    # Обычное поле select
    options = f.get("options") or []
    if not isinstance(options, list) or idx < 0 or idx >= len(options):
        await callback.answer("Некорректный выбор", show_alert=True)
        return
    set_nested_value(state["fields"], f["key"], options[idx])
    state["step"] += 1
    await callback.message.edit_reply_markup(reply_markup=None)
    await ask_next_field(user_id, callback.message)
    await callback.answer("Выбрано")


@router.callback_query(F.data.startswith("bool:"))
async def choose_bool(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_states or user_id not in ALLOWED_IDS:
        await callback.answer("🚫 Нет доступа", show_alert=True)
        return

    state = user_states[user_id]
    slug = state["template"]
    with open(f"templates/{slug}/fields.json", "r", encoding="utf-8") as f:
        template = json.load(f)
    fields = template["fields"]
    if state["step"] >= len(fields):
        await callback.answer()
        return
    f = fields[state["step"]]

    val_token = callback.data.split(":", 1)[1]
    value = "Да" if val_token == "1" else "Нет"

    # Массив (таблица) в процессе?
    if state.get("array") and state["array"].get("field_key") == f.get("key"):
        arr = state["array"]
        items = arr["items"]
        col = items[arr["col_index"]]
        if arr.get("current_row") is None:
            arr["current_row"] = {}
        arr["current_row"][col["key"]] = value
        arr["col_index"] += 1
        # переход дальше
        if arr["col_index"] >= len(items):
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Строка заполнена. Добавить ещё строку?", reply_markup=table_row_kb())
            await callback.answer("Выбрано")
            return
        next_col = items[arr["col_index"]]
        prompt = f"{f['label']} → Строка {arr['row_index'] + 1}. {next_col['label']} (пример: {next_col.get('placeholder','')})"
        await callback.message.edit_reply_markup(reply_markup=None)
        if next_col.get("type") == "select" and isinstance(next_col.get("options"), list) and next_col.get("options"):
            await callback.message.answer(prompt, reply_markup=select_kb(next_col["options"]))
        elif next_col.get("type") == "bool":
            await callback.message.answer(prompt, reply_markup=bool_kb())
        else:
            await callback.message.answer(prompt)
        await callback.answer("Выбрано")
        return

    # Обычное поле bool
    set_nested_value(state["fields"], f["key"], value)
    state["step"] += 1
    await callback.message.edit_reply_markup(reply_markup=None)
    await ask_next_field(user_id, callback.message)
    await callback.answer("Выбрано")


@router.callback_query(F.data.in_({"row:add", "row:done"}))
async def rows_control(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_states or user_id not in ALLOWED_IDS:
        await callback.answer("🚫 Нет доступа", show_alert=True)
        return

    state = user_states[user_id]
    slug = state["template"]
    with open(f"templates/{slug}/fields.json", "r", encoding="utf-8") as f:
        template = json.load(f)
    fields = template["fields"]
    if state["step"] >= len(fields):
        await callback.answer()
        return
    f = fields[state["step"]]
    arr = state.get("array")
    if not arr or arr.get("field_key") != f.get("key"):
        await callback.answer()
        return

    action = callback.data.split(":", 1)[1]
    if action == "done":
        # Зафиксировать текущую строку, если она завершена
        if arr.get("current_row") and len(arr["current_row"]) > 0:
            # Проверяем, что строка полностью заполнена
            if len(arr["current_row"]) == len(arr["items"]):
                arr["rows"].append(arr["current_row"])
                print(f"[DEBUG] Добавлена последняя строка: {arr['current_row']}")
            arr["current_row"] = None
        # Сохранить массив в итоговые поля и продолжить
        print(f"[DEBUG] Сохраняем массив с {len(arr['rows'])} строками для поля {f['key']}")
        set_nested_value(state["fields"], f["key"], arr["rows"])
        state["array"] = None
        state["step"] += 1
        await callback.message.edit_reply_markup(reply_markup=None)
        await ask_next_field(user_id, callback.message)
        await callback.answer("Готово")
        return

    if action == "add":
        # Проверяем общее количество строк (уже добавленные + текущая)
        total_rows = len(arr["rows"])
        if arr.get("current_row") and len(arr["current_row"]) > 0:
            total_rows += 1
        
        if total_rows >= 50:
            await callback.answer("⚠️ Достигнут лимит 50 строк", show_alert=True)
            # Сохраняем текущую строку если она есть
            if arr.get("current_row") and len(arr["current_row"]) == len(arr["items"]):
                arr["rows"].append(arr["current_row"])
                arr["current_row"] = None
            # как будто нажали done
            set_nested_value(state["fields"], f["key"], arr["rows"])
            state["array"] = None
            state["step"] += 1
            await callback.message.edit_reply_markup(reply_markup=None)
            await ask_next_field(user_id, callback.message)
            return
        # Зафиксировать предыдущую строку
        if arr.get("current_row") and len(arr["current_row"]) == len(arr["items"]):
            arr["rows"].append(arr["current_row"])
            print(f"[DEBUG] Добавлена строка {arr['row_index'] + 1}: {arr['current_row']}")
        # Начать новую строку
        arr["current_row"] = {}
        arr["row_index"] += 1
        arr["col_index"] = 0
        first_col = arr["items"][0]
        await callback.message.edit_reply_markup(reply_markup=None)
        prompt = f"{f['label']} → Строка {arr['row_index'] + 1}. {first_col['label']} (пример: {first_col.get('placeholder','')})"
        # Поддержка select/bool для первого поля новой строки
        if first_col.get("type") == "select" and isinstance(first_col.get("options"), list) and first_col.get("options"):
            await callback.message.answer(prompt, reply_markup=select_kb(first_col["options"]))
        elif first_col.get("type") == "bool":
            await callback.message.answer(prompt, reply_markup=bool_kb())
        else:
            await callback.message.answer(prompt)
        await callback.answer("Добавляем строку")
