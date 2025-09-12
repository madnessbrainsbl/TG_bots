-- Миграция для добавления таблицы reviews

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL
);

-- Индекс для быстрого поиска по пользователю и статусу модерации
CREATE INDEX IF NOT EXISTS ix_reviews_user_approved
    ON reviews (user_id, approved);
