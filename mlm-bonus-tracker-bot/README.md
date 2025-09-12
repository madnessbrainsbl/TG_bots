# MLM Bonus Tracker Bot (Telegram)

Телеграм-бот для партнёрской (MLM) сети: регистрация партнёров и лидов, заявки на сделки, автоматические начисления по 10 линиям, статусы партнёров, личный кабинет, выплаты, новости/обучение, админ-панель и уведомления.

## Основные возможности
- **Регистрация партнёров**: дерево до 10 линий, без дублей по телефону и Telegram ID, выдача реф-кода/ссылки и QR-кода
- **Добавление клиентов (лидов)** партнёрами: без дублей по телефону, автопривязка по реф-ссылке
- **Заявки на сделки** и подтверждение админом
- **MLM начисления**: автоначисления по 10 линиям (L1=1000 … L10=100)
- **Статусы партнёров**: автоматическое повышение по лестнице (Бронза → Серебро → … → Элитный) на основе подтверждённых сделок и прайс-планов
- **Личный кабинет**: баланс (потенциал/подтверждено), заявка на вывод
- **Контент (новости/обучение)**: учёт просмотров, реакции 👍/👎, базовая статистика, роль контент-менеджера
- **Отзывы партнёров**: модерация админом
- **Админ-панель**: подтверждение сделок/бонусов, списки партнёров/лидов/выплат, фильтры и экспорт CSV, навигация
- **Уведомления**: новый партнёр по сети, новый лид (админу/модератору), подтверждённая сделка, смена статуса, новая заявка на выплату
- **Команды и навигация**: /start, /help, /home, /admin, рабочие ReplyKeyboard, ссылки на соцсети
- **Согласие на ПДн при старте**: поддержка текста со ссылкой (см. ниже)

## Стек
- **Python 3.11**, **aiogram 3**
- **SQLAlchemy 2**, **Alembic**, **SQLite (aiosqlite)**
- **dotenv**, **sentry-sdk**, **prometheus-client** (метрики)

## Структура
- `main.py` — вход, регистрация роутеров, запуск бота
- `config.py` — настройки из окружения (`Settings`), `settings.DB_URL = sqlite+aiosqlite:///<path>`
- `db/models.py` — модели (`Base`, `User`, `Lead`, `Deal`, `Bonus`, `Payout`, `News`, `Instruction`, `Review`)
- `db/db.py` — движок и сессии, `init_db()` создаёт таблицы
- `alembic/` — конфигурация миграций; берёт URL из `DB_URL` или `alembic.ini`
- `handlers/` — обработчики: партнёры, лиды, сделки, бонусы, выплаты, контент, отзывы, админ и т.д.
- `mlm/` — логика дерева, статусов и начислений
- `monitoring/` — логирование, метрики, sentry

## Быстрый старт
1) Клонировать проект и активировать виртуальное окружение (по желанию).
2) Установить зависимости:
```bash
pip install -r requirements.txt
```
3) Создать файл `.env` рядом с `main.py` со значениями:
```env
BOT_TOKEN=123456:ABC...
BOT_USERNAME=YourBot
ADMIN_IDS=123456789
MANAGER_IDS=

# Путь к БД (создастся автоматически)
DB_PATH=bot.db
# или явный URL для Alembic/SQLAlchemy:
DB_URL=sqlite+aiosqlite:///./bot.db
# Для db/db.py fallback также понимается переменная
DATABASE_URL=sqlite+aiosqlite:///./bot.db

# Опционально: планы статусов и выплаты по уровням в JSON
STATUS_PLAN=[{"name":"bronze","min_points":0}, {"name":"silver","min_points":10}]
MLM_LEVELS={"L1":1000,"L2":900,"L3":800,"L4":700,"L5":600,"L6":500,"L7":400,"L8":300,"L9":200,"L10":100}

COMPANY_SITE_URL=https://prospisaniedolgov.ru/
LOG_LEVEL=INFO
SENTRY_DSN=
SENTRY_ENV=production
SENTRY_RELEASE=1.0.0
METRICS_PORT=9000
```
4) Инициализировать БД (любой из вариантов):
- Через Alembic:
```bash
alembic upgrade head
```
- Программно при старте (используется по умолчанию в `main.py`):
```python
from db import init_db
await init_db()  # создаст все таблицы по моделям
```
5) Запуск бота:
```bash
python main.py
```

## Важное про БД и миграции
- В проекте присутствуют два источника URL:
  - `config.settings.DB_URL` (используется Alembic через переменную окружения `DB_URL`)
  - `db/db.py` использует `DATABASE_URL` (fallback: `sqlite+aiosqlite:///./bot.db`)
- Настройте ОДИН и тот же путь/URL во всех местах (рекомендуется задать оба `DB_URL` и `DATABASE_URL` в `.env` одинаковыми), чтобы Alembic и runtime работали с одной БД.

### Ошибка sqlite3.OperationalError: no such table: users
Причина: таблицы ещё не созданы. Решения:
- Выполнить миграции:
```bash
alembic upgrade head
```
- Или создать таблицы программно:
```python
from db import init_db
await init_db()
```
- Убедиться, что URL совпадают. Если Alembic пишет в `./bot.db`, а приложение читает `./db.sqlite3`, получится «пустая» БД без таблиц.
- Проверить имя таблицы в модели `User` — `__tablename__ = "users"`. В проекте уже правильно настроено.

### Возможная несогласованность Base
- `db/models.py` определяет `Base = DeclarativeBase` и экспортирует его через `db/__init__.py`.
- `db/db.py` создаёт СВОЙ `Base = declarative_base()` — это другая `metadata`.
- В `init_db()` импортируются модели, но `create_all` вызывается на `Base` из `db/db.py`, а не на `db.models.Base`. Это работает, только если где-то регистрируется одинаковый `Base`. Если вы добавили новые модели и они не создаются — убедитесь, что используется один `Base`.

Рекомендации по унификации:
- Использовать `Base` из `db.models` в `db/db.py`.
- Держать единую переменную окружения с URL и использовать её везде (`DB_URL`).

Пример унификации (идея):
```python
# db/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import Base  # импортируем общий Base
from config import settings

engine = create_async_engine(settings.DB_URL, echo=False, future=True)
async_session_factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    import db.models  # ensure models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

## Согласие на обработку ПДн
При первом запуске добавьте шаг согласия с возможностью вывести ссылку на документ (например, Google Docs). Содержимое можно хранить в текстах или конфиге и отправлять как HTML с кликабельной ссылкой.

## Команды
- `/start` — регистрация/приветствие (+ согласие на ПДн)
- `/help` — помощь
- `/home` — главное меню
- `/admin` — вход в админ-панель (по роли)

## Тесты и отладка
- Логи: `logs/app.log` и уровень `LOG_LEVEL`
- Метрики Prometheus: порт `METRICS_PORT`
- Sentry: `SENTRY_DSN`

## Лицензия
Proprietary (или укажите вашу лицензию).
