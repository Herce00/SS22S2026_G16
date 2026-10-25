-- =============================================================================
-- 00_datasets.sql
-- Propósito : Crear los tres datasets del Proyecto 2 en la ubicación US.
-- Dueño     : Persona A (zona amarilla: la estructura de datasets es compartida).
-- Entradas  : ninguna.
-- Salidas   : ss2-g16-proyecto2.p2_a_trips, p2_contract, p2_b_ml.
-- Nota      : US es obligatorio. La fuente pública está en US y BigQuery no
--             consulta tablas de regiones distintas en una misma consulta.
--             Script idempotente (IF NOT EXISTS).
-- =============================================================================

-- Bloque 1: dataset de Persona A (tablas derivadas std/opt y vistas EDA).
CREATE SCHEMA IF NOT EXISTS `ss2-g16-proyecto2.p2_a_trips`
OPTIONS (
  location = 'US',
  description = 'Persona A: tablas derivadas (trips_2022_std, trips_2022_opt) y vistas v_eda_*.'
);

-- Bloque 2: dataset del contrato compartido entre A y B.
CREATE SCHEMA IF NOT EXISTS `ss2-g16-proyecto2.p2_contract`
OPTIONS (
  location = 'US',
  description = 'Contrato A-B: vista v_trips_clean con esquema congelado. Cambios solo de común acuerdo.'
);

-- Bloque 3: dataset de Persona B (features, modelos BQML, predicciones, vistas del tablero).
CREATE SCHEMA IF NOT EXISTS `ss2-g16-proyecto2.p2_b_ml`
OPTIONS (
  location = 'US',
  description = 'Persona B: features_*, modelos m_*, predicciones pred_* y vistas v_dash_*.'
);
