-- Миграция для обновления ролей пользователей

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'userrole'
          AND e.enumlabel = 'moderator'
    ) THEN
        ALTER TYPE userrole ADD VALUE 'moderator';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'userrole'
          AND e.enumlabel = 'partner'
    ) THEN
        ALTER TYPE userrole ADD VALUE 'partner';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'userrole'
          AND e.enumlabel = 'client'
    ) THEN
        ALTER TYPE userrole ADD VALUE 'client';
    END IF;
END $$;
