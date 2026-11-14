-- Postgres init script (runs once, on first initialisation of an empty volume).
-- The primary `app` database comes from POSTGRES_DB; integration tests use a
-- separate `app_test` database so they never touch dev data.
CREATE DATABASE app_test;
