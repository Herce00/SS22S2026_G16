-- =============================================================================
-- b_01_features.sql
-- Propósito : Construir la tabla de features para BigQuery ML a partir del
--             contrato: muestra determinística, features conocidas al inicio
--             del viaje (decisión M2), imputación (M6), etiquetas fare_amount
--             e is_tipped (M3) y columna de split temporal (M4, opción A).
-- Dueño     : Persona A (decisión D8 del steering; ruta B del flujo).
-- Entradas  : ss2-g16-proyecto2.p2_contract.v_trips_clean (fase 2; proyecta
--             p2_a_trips.trips_2022_opt; 34,796,108 filas).
--             bigquery-public-data.new_york_taxi_trips.taxi_zone_geom
--             (zone_id, zone_name, borough; decisión M7).
-- Salidas   : ss2-g16-proyecto2.p2_b_ml.features_trips.
--             Resultados de consulta F0 y V1 a V5.
-- Ejecución : Un bloque por archivo, primero con --dry_run, según
--             conventions.md:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --format=pretty < <archivo>"
-- Evidencia : Proyecto_2/evidencia/11_features.txt
-- Referencia: odd/tasks/p2-a-bqml.md (tarea T2, decisiones M2 a M7).
-- Notas     : - Muestra (M5): MOD(trip_id, 14) = 0. No se usa ABS porque
--               FARM_FINGERPRINT puede devolver el mínimo de INT64 y ABS
--               desborda con ese valor. MOD de un negativo da 0 cuando es
--               divisible, así que la selección sigue siendo correcta y
--               determinística.
--             - rate_code se guarda como texto con decimal ('1.0', '2.0',
--               ..., '99.0') y es NULL exactamente en los 1,169,077 viajes con
--               payment_type '0', los mismos que tienen passenger_count NULL
--               (08_eda_categorica.txt, C2a).
--             - taxi_zone_geom tiene 263 filas y 260 zone_id distintos; se usa
--               SELECT DISTINCT zone_id, zone_name, borough para no duplicar
--               viajes. Los ids 57, 105, 264 y 265 no tienen zona y su
--               borough se etiqueta como 'Desconocido'.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- F0: medición de valores extremos de fare_amount en la muestra.
-- Pregunta: ¿qué umbral de fare_amount separa los valores extremos sin
-- descartar viajes legítimos (aeropuertos, tarifas negociadas)?
-- Se mide sobre la misma muestra de F1, antes de aplicar el filtro. Los
-- percentiles salen de APPROX_QUANTILES(x, 10000) y son aproximados.
-- Resultado esperado: p99.9 muy por debajo de 300 y pocas filas por encima de
-- 300, lo que justifica el umbral de la regla de valores extremos.
-- -----------------------------------------------------------------------------

-- [F0]
SELECT
  COUNT(*) AS sample_rows,
  COUNTIF(fare_amount > 200) AS rows_gt_200,
  COUNTIF(fare_amount > 300) AS rows_gt_300,
  COUNTIF(fare_amount > 500) AS rows_gt_500,
  ROUND(100 * COUNTIF(fare_amount > 300) / COUNT(*), 4) AS pct_gt_300,
  APPROX_QUANTILES(fare_amount, 10000)[OFFSET(9900)] AS p99,
  APPROX_QUANTILES(fare_amount, 10000)[OFFSET(9990)] AS p99_9,
  APPROX_QUANTILES(fare_amount, 10000)[OFFSET(9999)] AS p99_99,
  MAX(fare_amount) AS max_fare
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`
WHERE MOD(trip_id, 14) = 0;


-- -----------------------------------------------------------------------------
-- F1: creación de p2_b_ml.features_trips.
-- Pregunta: ¿cómo queda el dataset limpio y sin leakage que consumen los
-- modelos de T3?
-- - zones: zonas deduplicadas (M7). Se une dos veces, para origen y destino.
-- - split_set (M4, opción A): 'train' = ene-sep, 'eval' = oct, 'new' = nov y
--   las 57 filas del 2022-12-01, que vienen en el archivo de noviembre.
-- - is_eval: columna booleana para el split CUSTOM de m_tip_logreg.
-- - pickup_month se conserva solo para el split y los reportes. No es input
--   de ningún modelo: el entrenamiento cubre los meses 1 a 9, así que los
--   meses 10 y 11 serían valores nunca vistos y el modelo extrapolaría.
-- - Features (M2): solo datos conocidos al inicio del viaje. pickup_hour y
--   pickup_dow pasan a STRING para que BQML los trate como categorías y no
--   como un orden lineal falso.
-- - Supuesto: trip_distance se trata como la distancia estimada de la ruta,
--   conocida al reservar el viaje (por ejemplo, la que calcula una app). En
--   el dato real es la distancia medida al terminar; el supuesto queda
--   explícito.
-- - Imputación (M6): passenger_count NULL pasa a 1 con la marca
--   passenger_missing; rate_code NULL pasa a 'NA'.
-- - payment_type se conserva solo para filtrar (M3); nunca es feature del
--   modelo de propina.
-- - Etiquetas: fare_amount (regresión) e is_tipped (clasificación), que solo
--   tiene valor con tarjeta (payment_type = '1') y es NULL en los demás
--   pagos (M3).
-- - Regla de valores extremos: se excluyen las filas con fare_amount > 300.
--   En F0, 50 de 2,486,865 filas de la muestra (0.002 %) superan 300, con
--   p99.9 = 105 y p99.99 = 216. Un corte en el p99.9 recortaría la cola de
--   tarifas Newark, Nassau/Westchester y negociada (promedios de USD 68.59
--   a 74.01, C3a de 08_eda_categorica.txt), que probablemente son viajes
--   legítimos (hipótesis). 300 queda por encima del p99.99 y quita valores
--   como el máximo de la muestra, 395,844.94.
-- -----------------------------------------------------------------------------

-- [F1]
CREATE OR REPLACE TABLE `ss2-g16-proyecto2.p2_b_ml.features_trips` AS
WITH zones AS (
  SELECT DISTINCT zone_id, zone_name, borough
  FROM `bigquery-public-data.new_york_taxi_trips.taxi_zone_geom`
)
SELECT
  t.trip_id,
  CASE
    WHEN t.pickup_month <= 9 THEN 'train'
    WHEN t.pickup_month = 10 THEN 'eval'
    ELSE 'new'
  END AS split_set,
  t.pickup_month = 10 AS is_eval,
  t.pickup_month,
  CAST(t.pickup_hour AS STRING) AS pickup_hour,
  CAST(t.pickup_dow AS STRING) AS pickup_dow,
  t.trip_distance,
  IFNULL(t.passenger_count, 1) AS passenger_count_imp,
  t.passenger_count IS NULL AS passenger_missing,
  t.pickup_location_id,
  t.dropoff_location_id,
  IFNULL(pz.borough, 'Desconocido') AS pickup_borough,
  IFNULL(dz.borough, 'Desconocido') AS dropoff_borough,
  t.vendor_id,
  IFNULL(t.rate_code, 'NA') AS rate_code_imp,
  t.payment_type,
  t.fare_amount,
  CASE WHEN t.payment_type = '1' THEN t.tip_amount > 0 END AS is_tipped
FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean` AS t
LEFT JOIN zones AS pz
  ON t.pickup_location_id = pz.zone_id
LEFT JOIN zones AS dz
  ON t.dropoff_location_id = dz.zone_id
WHERE MOD(t.trip_id, 14) = 0
  AND t.fare_amount <= 300;


-- -----------------------------------------------------------------------------
-- V1: filas por split.
-- Pregunta: ¿cada split tiene filas y los tres suman el total de la tabla?
-- Resultado esperado: train, eval y new con filas > 0; la suma igual al total
-- de la tabla, que debe ser al menos 1,000,000.
-- -----------------------------------------------------------------------------

-- [V1]
SELECT
  split_set,
  COUNT(*) AS rows_split,
  SUM(COUNT(*)) OVER () AS rows_total,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_rows,
  MIN(pickup_month) AS min_month,
  MAX(pickup_month) AS max_month
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
GROUP BY split_set
ORDER BY min_month;


-- -----------------------------------------------------------------------------
-- V2: nulos por feature después de la imputación.
-- Pregunta: ¿queda algún NULL en las features de los modelos?
-- Resultado esperado: 0 en todas las columnas.
-- -----------------------------------------------------------------------------

-- [V2]
SELECT
  COUNTIF(pickup_hour IS NULL) AS null_pickup_hour,
  COUNTIF(pickup_dow IS NULL) AS null_pickup_dow,
  COUNTIF(trip_distance IS NULL) AS null_trip_distance,
  COUNTIF(passenger_count_imp IS NULL) AS null_passenger_count_imp,
  COUNTIF(passenger_missing IS NULL) AS null_passenger_missing,
  COUNTIF(pickup_location_id IS NULL) AS null_pickup_location_id,
  COUNTIF(dropoff_location_id IS NULL) AS null_dropoff_location_id,
  COUNTIF(pickup_borough IS NULL) AS null_pickup_borough,
  COUNTIF(dropoff_borough IS NULL) AS null_dropoff_borough,
  COUNTIF(vendor_id IS NULL) AS null_vendor_id,
  COUNTIF(rate_code_imp IS NULL) AS null_rate_code_imp,
  COUNTIF(fare_amount IS NULL) AS null_fare_amount,
  COUNTIF(passenger_missing) AS imputed_passenger,
  COUNTIF(rate_code_imp = 'NA') AS imputed_rate_code
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`;


-- -----------------------------------------------------------------------------
-- V3: balance de la etiqueta is_tipped.
-- Pregunta: ¿is_tipped solo tiene valor con tarjeta y qué porcentaje deja
-- propina en cada split?
-- Resultado esperado: tipped_non_null = card_rows en cada split,
-- non_card_with_label = 0 y pct_tipped cercano al 96 % (C8a de
-- 08_eda_categorica.txt).
-- -----------------------------------------------------------------------------

-- [V3]
SELECT
  split_set,
  COUNTIF(payment_type = '1') AS card_rows,
  COUNTIF(is_tipped IS NOT NULL) AS tipped_non_null,
  COUNTIF(payment_type != '1' AND is_tipped IS NOT NULL) AS non_card_with_label,
  COUNTIF(is_tipped) AS tipped_true,
  COUNTIF(NOT is_tipped) AS tipped_false,
  ROUND(100 * COUNTIF(is_tipped) / COUNTIF(is_tipped IS NOT NULL), 2) AS pct_tipped
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
GROUP BY split_set
ORDER BY MIN(pickup_month);


-- -----------------------------------------------------------------------------
-- V4: estadísticas de fare_amount por split.
-- Pregunta: ¿la etiqueta de regresión tiene una distribución parecida en los
-- tres splits y respeta el umbral de valores extremos?
-- Resultado esperado: max_fare <= 300 en todos los splits. Los percentiles
-- salen de APPROX_QUANTILES(x, 100) y son aproximados.
-- -----------------------------------------------------------------------------

-- [V4]
SELECT
  split_set,
  COUNT(*) AS rows_split,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  APPROX_QUANTILES(fare_amount, 100)[OFFSET(50)] AS p50_fare,
  APPROX_QUANTILES(fare_amount, 100)[OFFSET(99)] AS p99_fare,
  MIN(fare_amount) AS min_fare,
  MAX(fare_amount) AS max_fare
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
GROUP BY split_set
ORDER BY MIN(pickup_month);


-- -----------------------------------------------------------------------------
-- V5: cardinalidad de las features categóricas.
-- Pregunta: ¿cuántas categorías distintas ve cada modelo?
-- Resultado esperado: como máximo 265 zonas por lado (ids 1 a 265), 7
-- boroughs (los 6 de taxi_zone_geom: Manhattan, Queens, Brooklyn, Bronx,
-- Staten Island y EWR, más 'Desconocido'), 8 valores de rate_code_imp (7
-- códigos más 'NA'), 4 vendor_id (1, 2, 5 y 6), 24 horas y 7 días.
-- -----------------------------------------------------------------------------

-- [V5]
SELECT
  COUNT(DISTINCT pickup_location_id) AS pickup_zones,
  COUNT(DISTINCT dropoff_location_id) AS dropoff_zones,
  COUNT(DISTINCT pickup_borough) AS pickup_boroughs,
  COUNT(DISTINCT dropoff_borough) AS dropoff_boroughs,
  COUNT(DISTINCT rate_code_imp) AS rate_code_values,
  COUNT(DISTINCT vendor_id) AS vendor_values,
  COUNT(DISTINCT pickup_hour) AS hour_values,
  COUNT(DISTINCT pickup_dow) AS dow_values
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`;
