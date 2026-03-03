import os
import json
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        # ✅ Основные параметры
        self.BOT_TOKEN: str = os.getenv("BOT_TOKEN")
        self.BOT_USERNAME: str = os.getenv("BOT_USERNAME", "UnknownBot")
        self.ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
        self.MANAGER_IDS = [int(x) for x in os.getenv("MANAGER_IDS", "").split(",") if x]

        # ✅ Подключение к БД
        self.DB_PATH = os.getenv("DB_PATH", "db.sqlite3")
        self.DB_URL = f"sqlite+aiosqlite:///{self.DB_PATH}"

        # ✅ Логи и мониторинг
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.METRICS_PORT = int(os.getenv("METRICS_PORT", "9000"))
        self.SENTRY_DSN = os.getenv("SENTRY_DSN", "")
        self.SENTRY_ENV = os.getenv("SENTRY_ENV", "production")
        self.SENTRY_RELEASE = os.getenv("SENTRY_RELEASE", "1.0.0")

        # ✅ Константы для MLM логики
        # План статусов (читаем JSON из .env)
        status_plan_raw = os.getenv("STATUS_PLAN")
        self.STATUS_PLAN = json.loads(status_plan_raw) if status_plan_raw else []

        # Выплаты по уровням
        mlm_levels_raw = os.getenv("MLM_LEVELS")
        self.LINE_PAYOUTS = json.loads(mlm_levels_raw) if mlm_levels_raw else {}

        # ✅ Сайт компании
        self.COMPANY_SITE_URL = os.getenv("COMPANY_SITE_URL", "https://prospisaniedolgov.ru/")

        # ✅ Приветственное сообщение
        self.welcome_message = """
**Куда Мы Идем: Миссия Помогать 150 000 Людям в Год** 🌟

Каждый из нас сталкивается с вызовами, которые порой кажутся непреодолимыми. 
Для многих людей долговые обязательства становятся таким вызовом, затмевающим радость жизни и ограничивающим возможности. 
Но мы твёрдо верим, что вместе мы можем изменить эту ситуацию и вернуть людям свободу и уверенность в завтрашнем дне. 🌈

Наша цель — помогать 150 000 людям в год списать их долги. 
Это амбициозная задача, но мы убеждены, что она достижима. Почему? 
Потому что у нас есть вы — команда единомышленников, готовых внести свой вклад в это важное дело. 🤝

**Почему это важно?**

Долги могут стать настоящим бременем, влияющим на все аспекты жизни человека. 
Они ограничивают возможности, создают стресс и мешают двигаться вперёд. 
Освобождение от долгов — это не просто финансовая выгода, это новый старт, шанс на лучшее будущее. 🚀

**Как мы этого достигнем?**

1️⃣ Командная работа — только объединив усилия, мы сможем достичь нашей цели.  
2️⃣ Индивидуальный подход — каждая история уникальна, и мы будем искать решения для каждого человека.  
3️⃣ Образование и поддержка — будем не только помогать списывать долги, но и обучать, как избежать их в будущем. 📚

**Вместе мы можем больше** 🌟

С уважением и верой в успех,  
@alexey62ryazan
"""


# Экземпляр настроек для использования в проекте
settings = Settings()
