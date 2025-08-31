# Telegram-бот генерации юридических документов

Простой бот: пользователь выбирает шаблон, отвечает на вопросы, получает DOCX и PDF. Доступ закрытый по списку ID. Поддержка табличных полей (array), select и bool.

## Запуск локально

1. Требования:
   - Python 3.10+
   - LibreOffice (для PDF):
     - Windows: установите LibreOffice и убедитесь, что `soffice` в PATH (или в `C:\\Program Files\\LibreOffice\\program\\soffice.exe`).
     - Linux: `sudo apt-get install libreoffice`.
2. Склонируйте/откройте проект.
3. Создайте и заполните `.env` (см. `.env.example`).
4. Установите зависимости:
   ```
   python -m venv .venv
   .venv/Scripts/pip install -r requirements.txt   # Windows
   # или
   source .venv/bin/activate && pip install -r requirements.txt  # Linux/macOS
   ```
5. Запустите бота:
   ```
   python main.py
   ```

## Запуск в Docker (рекомендуется для PDF)

1. Создайте `.env` рядом с проектом (см. `.env.example`).
2. Соберите образ:
   ```
   docker build -t documents-bot .
   ```
3. Запуск:
   ```
   docker run --rm --env-file .env documents-bot
   ```

В контейнере уже установлены LibreOffice и шрифты, PDF будет создаваться автоматически.

## Шаблоны

- Папка `templates/<slug>/` должна содержать:
  - `template.docx` (или `template11.docx`/`template1.docx`)
  - `fields.json` с полями вида:
    ```json
    {
      "slug": "example",
      "name": "Пример",
      "fields": [
        { "key": "fio", "label": "ФИО", "type": "string", "required": true, "placeholder": "Иванов Иван" },
        { "key": "agree", "label": "Согласие", "type": "bool", "required": true },
        { "key": "variant", "label": "Вариант", "type": "select", "options": ["A", "B", "C"] },
        {
          "key": "works",
          "label": "Таблица работ",
          "type": "array",
          "items": [
            { "key": "title", "label": "Название", "type": "string" },
            { "key": "kind", "label": "Тип", "type": "select", "options": ["Автор", "Исполнитель"] }
          ]
        }
      ]
    }
    ```

- Для массивов (array) бот умеет автоматически собирать таблицы в DOCX, если в шаблоне стоит маркер `__TABLE_<key>__` (или `<<TABLE_<key>>>`).

## Имена файлов

Имена при отправке: `<slug>_YYYYMMDD_HHMM.docx` и `.pdf`.

## Доступ и админка

- Доступ по ID из `.env`:
  - `TELEGRAM_ALLOWED_IDS=...`
  - `TELEGRAM_ADMIN_IDS=...`
- Команда `/admin` — включение/выключение шаблонов (флаги в `enabled.json`).

## Примечания

- Если PDF не создаётся локально, проверьте установку LibreOffice. В Docker этот шаг уже настроен.
- Временные файлы удаляются после отправки пользователю.
- TELEGRAM_BOT_TOKEN=7336134039:AAFwp52mTkjV71AMuvoNJzHcXs1s2ZFMH9o  @FPmeneger_bot
- TELEGRAM_ALLOWED_IDS=1777340484
