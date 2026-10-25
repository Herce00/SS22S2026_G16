-- =============================================================================
-- 02_validaciones_contrato.sql
-- Propósito : Validar la vista del contrato p2_contract.v_trips_clean. Las mismas
--             consultas sirven de prueba de regresión entre la fase 1 (tabla
--             pública con filtros) y la fase 2 (proyección de trips_2022_opt).
-- Dueño     : Persona A (zona amarilla).
-- Entradas  : ss2-g16-proyecto2.p2_contract.v_trips_clean
--             ss2-g16-proyecto2.p2_contract.INFORMATION_SCHEMA.COLUMNS
-- Salidas   : solo resultados de consulta; se guardan en Proyecto_2/evidencia/
--             (02_contrato_schema.txt, 03_contrato_validaciones.txt y
--             06_contrato_fase2.txt).
-- Uso       : cada SELECT es independiente. Se ejecuta uno por uno, primero con
--             --dry_run para registrar los bytes procesados. Los resultados
--             esperados son exactos: cualquier diferencia entre fases es una
--             regresión del contrato.
-- =============================================================================

-- Validación (a): conteo total de filas.
-- Pregunta : ¿la vista conserva un volumen suficiente para BigQuery ML?
-- Esperado : total_rows >= 1,000,000 (valor observado: 34,796,108).
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

-- Validación (d): violaciones de los 7 filtros de limpieza.
-- Pregunta : ¿queda alguna fila que incumpla alguno de los 7 filtros del
--            contrato? Los nulos cuentan como violación donde el filtro los
--            descarta. La duración usa TIMESTAMP_DIFF en MINUTE, igual que el
--            filtro original.
-- Esperado : las siete columnas en 0.
SELECT
  COUNTIF(pickup_datetime IS NULL OR pickup_datetime < '2022-01-01' OR pickup_datetime >= '2023-01-01') AS bad_pickup_date_range,
  COUNTIF(dropoff_datetime IS NULL OR dropoff_datetime <= pickup_datetime) AS bad_dropoff_not_after_pickup,
  COUNTIF(TIMESTAMP_DIFF(dropoff_datetime, pickup_datetime, MINUTE) > 360) AS bad_duration_over_360_min,
  COUNTIF(trip_distance IS NULL OR trip_distance <= 0 OR trip_distance > 100) AS bad_trip_distance,
  COUNTIF(fare_amount IS NULL OR fare_amount <= 0) AS bad_fare_amount,
  COUNTIF(total_amount IS NULL OR total_amount <= 0) AS bad_total_amount,
  COUNTIF(passenger_count IS NOT NULL AND passenger_count NOT BETWEEN 1 AND 6) AS bad_passenger_count
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`;

-- Validación (e1): cobertura exacta de fechas.
-- Pregunta : ¿qué rango de fechas cubre la vista y cuántos días distintos tiene?
--            La fuente no tiene archivo de diciembre (data_file_month va de 1 a
--            11); el 2022-12-01 llega como desborde del archivo de noviembre.
-- Esperado : min_pickup_date = 2022-01-01, max_pickup_date = 2022-12-01 y
--            distinct_pickup_dates = 335.
SELECT
  MIN(pickup_date) AS min_pickup_date,
  MAX(pickup_date) AS max_pickup_date,
  COUNT(DISTINCT pickup_date) AS distinct_pickup_dates
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`;

-- Validación (e2): filas por mes de recogida.
-- Pregunta : ¿cuántas filas tiene cada mes? B lo necesita para el split temporal.
-- Esperado : exactamente estas 12 filas.
--            mes  1 = 2,367,647   mes  7 = 3,042,344
--            mes  2 = 2,866,677   mes  8 = 3,019,682
--            mes  3 = 3,489,827   mes  9 = 3,052,193
--            mes  4 = 3,463,974   mes 10 = 3,516,529
--            mes  5 = 3,445,399   mes 11 = 3,119,033
--            mes  6 = 3,412,746   mes 12 =        57 (desborde del 2022-12-01)
SELECT
  pickup_month,
  COUNT(*) AS rows_in_month
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`
GROUP BY pickup_month
ORDER BY pickup_month;

-- Validación (e3): totales del split temporal de la opción A.
-- Pregunta : ¿cuántas filas caen en cada conjunto del split propuesto?
--            Entrenamiento = meses 1 a 9; evaluación = mes 10; nuevos
--            registros = meses 11 y 12 (las 57 filas del 2022-12-01 incluidas).
-- Esperado : train = 28,160,489; eval = 3,516,529; new = 3,119,090.
SELECT
  CASE
    WHEN pickup_month BETWEEN 1 AND 9 THEN 'train'
    WHEN pickup_month = 10 THEN 'eval'
    ELSE 'new'
  END AS split_bucket,
  COUNT(*) AS rows_in_bucket
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`
GROUP BY split_bucket
ORDER BY MIN(pickup_month);

-- Validación (f): huella de la fila completa.
-- Pregunta : ¿el contenido de la vista es idéntico entre fases, columna por
--            columna? TO_JSON_STRING(t) serializa las 19 columnas con sus
--            nombres y en su orden; BIT_XOR no depende del orden de las filas.
-- Esperado : n = 34,796,108 y row_fp igual al valor de la línea base de la
--            fase 1 registrado en 06_contrato_fase2.txt.
SELECT
  COUNT(*) AS n,
  BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS row_fp
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean` AS t;
