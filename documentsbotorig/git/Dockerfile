# syntax=docker/dockerfile:1

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Устанавливаем LibreOffice (для конвертации DOCX -> PDF) и шрифты
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libreoffice \
       libreoffice-writer \
       fonts-dejavu-core \
       fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY . /app

# Непривилегированный пользователь (опционально)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "main.py"]
