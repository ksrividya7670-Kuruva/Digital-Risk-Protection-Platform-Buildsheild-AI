-- ============================================================
-- BrandShield AI — PostgreSQL Initialization
-- This script runs once when the container is first created.
-- It verifies the database is accessible.
-- The actual schema is managed by Alembic migrations.
-- ============================================================

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for text similarity search

-- Log that init ran
DO $$
BEGIN
    RAISE NOTICE 'BrandShield AI database initialized successfully.';
END $$;
