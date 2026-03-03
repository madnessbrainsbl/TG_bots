# Telegram Relay Bot

Чистая версия проекта для GitHub: без токенов и личных данных.

## Что внутри

- `relay_bot.py` - простой relay между двумя чатами (преподаватель <-> ученик)
- `forum_relay_bot.py` - relay между форумом преподавателя и чатами учеников по темам
- `relay_config.example.json` - шаблон конфига для простого режима
- `forum_relay_config.example.json` - шаблон конфига для форумного режима
- `.env.example` - шаблон переменных окружения

## Быстрый старт

1) Установите зависимости:

```bash
pip install -r requirements.txt
```

2) Создайте рабочие конфиги из шаблонов.

Windows (cmd):

```bat
copy relay_config.example.json relay_config.json
copy forum_relay_config.example.json forum_relay_config.json
```

Linux/Mac:

```bash
cp relay_config.example.json relay_config.json
cp forum_relay_config.example.json forum_relay_config.json
```

3) Укажите токены ботов через переменные окружения.

Windows (cmd):

```bat
set RELAY_BOT_TOKEN=YOUR_RELAY_TOKEN
set FORUM_BOT_TOKEN=YOUR_FORUM_TOKEN
```

PowerShell:

```powershell
$env:RELAY_BOT_TOKEN="YOUR_RELAY_TOKEN"
$env:FORUM_BOT_TOKEN="YOUR_FORUM_TOKEN"
```

Linux/Mac:

```bash
export RELAY_BOT_TOKEN="YOUR_RELAY_TOKEN"
export FORUM_BOT_TOKEN="YOUR_FORUM_TOKEN"
```

4) Запуск.

- `run_relay.bat` - простой режим
- `run_forum_bot.bat` - форумный режим

## Для публикации на GitHub

- В репозитории нет зашитых токенов
- Локальные конфиги (`relay_config.json`, `forum_relay_config.json`) игнорируются через `.gitignore`
- Используйте только шаблоны `*.example.json` и `.env.example`
