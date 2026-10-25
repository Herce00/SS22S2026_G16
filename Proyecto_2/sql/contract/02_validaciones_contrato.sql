-- =============================================================================
-- 02_validaciones_contrato.sql
-- Propósito : Validar la vista del contrato p2_contract.v_trips_clean (fase 1).
-- Dueño     : Persona A (zona amarilla).
-- Entradas  : ss2-g16-proyecto2.p2_contract.v_trips_clean
--             ss2-g16-proyecto2.p2_contract.INFORMATION_SCHEMA.COLUMNS
-- Salidas   : solo resultados de consulta; se guardan en Proyecto_2/evidencia/
--             (02_contrato_schema.txt y 03_contrato_validaciones.txt).
-- Uso       : cada SELECT es independiente. Se ejecuta uno por uno, primero con
--             --dry_run para registrar los bytes procesados.
-- =============================================================================

-- Validación (a): conteo total de filas.
-- Pregunta : ¿la vista conserva un volumen suficiente para BigQuery ML?
-- Esperado : total_rows >= 1,000,000.
SELECT
  COUNT(*) AS total_rows
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`;

-- Validación (b): esquema publicado de la vista.
-- Pregunta : ¿los nombres, tipos y orden de las columnas son los del contrato?
-- Esperado : 19 columnas, en el orden y con los tipos de architecture.md.
SELECT
  ordinal_position,
  column_name,
  data_type
FROM `ss2-g16-proyecto2.p2_contract.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'v_trips_clean'
ORDER BY ordinal_position;

-- Validación (c): unicidad de trip_id.
-- Pregunta : ¿hay dos viajes con el mismo trip_id?
-- Esperado : duplicated_trip_ids = 0.
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT trip_id) AS distinct_trip_ids,
  COUNT(*) - COUNT(DISTINCT trip_id) AS duplicated_trip_ids
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`;

-- Validación (d): muestra de filtros de limpieza.
-- Pregunta : ¿quedan filas que violen el rango de fechas, la distancia o los montos?
-- Esperado : las cuatro columnas en 0.
SELECT
  COUNTIF(pickup_datetime < '2022-01-01' OR pickup_datetime >= '2023-01-01') AS bad_pickup_date_range,
  COUNTIF(trip_distance <= 0 OR trip_distance > 100) AS bad_trip_distance,
  COUNTIF(fare_amount <= 0) AS bad_fare_amount,
  COUNTIF(total_amount <= 0) AS bad_total_amount
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`;

-- Validación (e1): cobertura de fechas.
-- Pregunta : ¿la vista cubre todo 2022 y nada fuera de ese año?
-- Esperado : min_pickup_date >= 2022-01-01 y max_pickup_date <= 2022-12-31.
SELECT
  MIN(pickup_date) AS min_pickup_date,
  MAX(pickup_date) AS max_pickup_date
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`;

-- Validación (e2): filas por mes de recogida.
-- Pregunta : ¿cuántas filas tiene cada mes? B lo necesita para el split
--            entrenamiento (ene-sep), evaluación (oct-nov) y nuevos (dic).
-- Esperado : 12 meses, todos con filas.
SELECT
  pickup_month,
  COUNT(*) AS rows_in_month
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`
GROUP BY pickup_month
ORDER BY pickup_month;
