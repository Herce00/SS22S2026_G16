-- =============================================================================
-- Inicialización de Schemas del Data Warehouse (sgfood_dw)
-- Schemas: raw (fuente/ingesta), staging (limpieza dbt), marts (modelo analítico)
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- Otorgar permisos al usuario del DW en los schemas creados
GRANT ALL ON SCHEMA raw TO CURRENT_USER;
GRANT ALL ON SCHEMA staging TO CURRENT_USER;
GRANT ALL ON SCHEMA marts TO CURRENT_USER;

COMMENT ON SCHEMA raw IS 'Capa de datos crudos fiel a la fuente, poblada por Python';
COMMENT ON SCHEMA staging IS 'Capa de normalización y limpieza inicial modelada con dbt';
COMMENT ON SCHEMA marts IS 'Capa analítica dimensional (hechos y dimensiones) modelada con dbt';
