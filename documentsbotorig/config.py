import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден! Проверь .env файл")

def parse_ids(env_var):
    return [int(x.strip()) for x in os.getenv(env_var, "").split(",") if x.strip().isdigit()]

ALLOWED_IDS = parse_ids("TELEGRAM_ALLOWED_IDS")
ADMIN_IDS = parse_ids("TELEGRAM_ADMIN_IDS")

ENABLED_PATH = "enabled.json"
