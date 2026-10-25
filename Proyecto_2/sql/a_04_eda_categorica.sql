-- =============================================================================
-- a_04_eda_categorica.sql
-- Propósito : Análisis exploratorio de las variables categóricas de los viajes
--             de 2022: tipo de pago (con la caracterización del código 0),
--             tarifa (rate_code), número de pasajeros, proveedor, zonas y
--             boroughs de origen y destino, y propinas (prueba de la decisión
--             E4).
-- Dueño     : Persona A (zona verde).
-- Entradas  : ss2-g16-proyecto2.p2_a_trips.trips_2022_opt (decisión E1;
--             34,796,108 filas, mismo esquema que el contrato).
--             bigquery-public-data.new_york_taxi_trips.taxi_zone_geom
--             (decisión E2; zone_id, zone_name, borough).
-- Salidas   : Ninguna tabla. Resultados de consulta C1 a C8.
-- Ejecución : Una consulta por archivo, primero con --dry_run, según
--             conventions.md:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --format=pretty < <archivo>"
-- Evidencia : Proyecto_2/evidencia/08_eda_categorica.txt
-- Referencia: odd/tasks/p2-a-eda.md (tarea T3, decisiones E2, E3 y E4).
-- Notas     : - rate_code se guarda como texto con decimal ('1.0', '2.0',
--               ..., '99.0'); los CASE usan ese formato.
--             - taxi_zone_geom tiene 263 filas pero 260 zone_id distintos:
--               las zonas 56 y 103 tienen varios polígonos con el mismo nombre
--               y borough. Unir contra la tabla cruda duplicaría viajes, así
--               que cada bloque usa SELECT DISTINCT zone_id, zone_name,
--               borough sin la columna geográfica.
--             - Los códigos de payment_type y rate_code se traducen según el
--               diccionario de datos de TLC (decisión E3).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- C1: distribución por tipo de pago.
-- Pregunta: ¿cómo pagan los pasajeros y cuánto gastan y dejan de propina según
-- el medio de pago?
-- CASE traduce el código de TLC. El porcentaje usa SUM(COUNT(*)) OVER ().
-- Control: la suma de trips debe ser 34,796,108.
-- -----------------------------------------------------------------------------

-- [C1]
SELECT
  payment_type,
  CASE payment_type
    WHEN '1' THEN 'Tarjeta de crédito'
    WHEN '2' THEN 'Efectivo'
    WHEN '3' THEN 'Sin cargo'
    WHEN '4' THEN 'Disputa'
    WHEN '5' THEN 'Desconocido'
    WHEN '6' THEN 'Anulado'
    WHEN '0' THEN 'Sin código (0)'
    ELSE 'Otro'
  END AS payment_label,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(AVG(total_amount), 2) AS avg_total,
  ROUND(AVG(tip_amount), 2) AS avg_tip
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY payment_type, payment_label
ORDER BY payment_type;


-- -----------------------------------------------------------------------------
-- C2a: código 0, coincidencia con passenger_count y rate_code nulos.
-- Pregunta: ¿los viajes con payment_type '0' son los mismos que no tienen
-- passenger_count ni rate_code?
-- Si code0 = null_passenger_count = code0_and_null_passenger, los dos
-- conjuntos son idénticos. Lo mismo para rate_code.
-- -----------------------------------------------------------------------------

-- [C2a]
SELECT
  COUNTIF(payment_type = '0') AS code0,
  COUNTIF(passenger_count IS NULL) AS null_passenger_count,
  COUNTIF(payment_type = '0' AND passenger_count IS NULL) AS code0_and_null_passenger,
  COUNTIF(payment_type = '0' AND passenger_count IS NOT NULL) AS code0_with_passenger,
  COUNTIF(payment_type != '0' AND passenger_count IS NULL) AS null_passenger_other_code,
  COUNTIF(rate_code IS NULL) AS null_rate_code,
  COUNTIF(payment_type = '0' AND rate_code IS NULL) AS code0_and_null_rate_code
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`;


-- -----------------------------------------------------------------------------
-- C2b: código 0, distribución de rate_code y vendor_id.
-- Pregunta: ¿qué tarifa y qué proveedor tienen los viajes con código 0?
-- UNION ALL apila las dos dimensiones; el porcentaje se calcula dentro de cada
-- dimensión con PARTITION BY.
-- -----------------------------------------------------------------------------

-- [C2b]
WITH code0 AS (
  SELECT rate_code, vendor_id
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  WHERE payment_type = '0'
),
by_dimension AS (
  SELECT 'rate_code' AS dimension, IFNULL(rate_code, 'NULL') AS value, COUNT(*) AS trips
  FROM code0
  GROUP BY value
  UNION ALL
  SELECT 'vendor_id' AS dimension, IFNULL(vendor_id, 'NULL') AS value, COUNT(*) AS trips
  FROM code0
  GROUP BY value
)
SELECT
  dimension,
  value,
  trips,
  ROUND(100 * trips / SUM(trips) OVER (PARTITION BY dimension), 2) AS pct_within_dimension
FROM by_dimension
ORDER BY dimension, trips DESC;


-- -----------------------------------------------------------------------------
-- C2c: código 0, participación por mes.
-- Pregunta: ¿el código 0 aparece de forma pareja en el año o se concentra en
-- algunos meses?
-- -----------------------------------------------------------------------------

-- [C2c]
SELECT
  pickup_month,
  COUNT(*) AS trips,
  COUNTIF(payment_type = '0') AS code0_trips,
  ROUND(100 * COUNTIF(payment_type = '0') / COUNT(*), 2) AS pct_code0
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY pickup_month
ORDER BY pickup_month;


-- -----------------------------------------------------------------------------
-- C2d: código 0 frente a tarjeta (1) y efectivo (2).
-- Pregunta: ¿los viajes con código 0 se parecen en tarifa, propina, distancia
-- y duración a los pagados con tarjeta o a los pagados en efectivo?
-- -----------------------------------------------------------------------------

-- [C2d]
SELECT
  payment_type,
  COUNT(*) AS trips,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  ROUND(AVG(tip_amount), 2) AS avg_tip,
  ROUND(100 * COUNTIF(tip_amount > 0) / COUNT(*), 2) AS pct_tipped,
  ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
  ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
  ROUND(AVG(total_amount), 2) AS avg_total
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
WHERE payment_type IN ('0', '1', '2')
GROUP BY payment_type
ORDER BY payment_type;


-- -----------------------------------------------------------------------------
-- C3a: distribución por tipo de tarifa (rate_code).
-- Pregunta: ¿qué tarifas se usan y cuánto cuesta cada una?
-- CASE traduce el código de TLC. Los valores nulos se etiquetan aparte porque
-- coinciden con el código 0 de pago (C2a); 99 y cualquier otro valor quedan
-- como "Desconocido".
-- -----------------------------------------------------------------------------

-- [C3a]
SELECT
  rate_code,
  CASE
    WHEN rate_code IS NULL THEN 'Sin código (NULL)'
    WHEN rate_code = '1.0' THEN 'Estándar'
    WHEN rate_code = '2.0' THEN 'JFK'
    WHEN rate_code = '3.0' THEN 'Newark'
    WHEN rate_code = '4.0' THEN 'Nassau/Westchester'
    WHEN rate_code = '5.0' THEN 'Negociada'
    WHEN rate_code = '6.0' THEN 'Grupal'
    ELSE 'Desconocido'
  END AS rate_label,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  ROUND(APPROX_QUANTILES(fare_amount, 100)[OFFSET(50)], 2) AS p50_fare
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY rate_code, rate_label
ORDER BY rate_code;


-- -----------------------------------------------------------------------------
-- C3b: tarifas más frecuentes dentro de la tarifa JFK (rate_code '2.0').
-- Pregunta: ¿la tarifa JFK es un monto fijo? Prueba la hipótesis de T2 de que
-- la cola de fare_amount cerca de USD 52 corresponde a esa tarifa.
-- -----------------------------------------------------------------------------

-- [C3b]
SELECT
  fare_amount,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_jfk_trips
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
WHERE rate_code = '2.0'
GROUP BY fare_amount
QUALIFY ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, fare_amount) <= 5
ORDER BY trips DESC, fare_amount;


-- -----------------------------------------------------------------------------
-- C3c: tipo de tarifa de los viajes con fare_amount = 52.
-- Pregunta: ¿qué parte de los viajes de USD 52 exactos es tarifa JFK?
-- Complementa C3b en sentido inverso.
-- -----------------------------------------------------------------------------

-- [C3c]
SELECT
  IFNULL(rate_code, 'NULL') AS rate_code,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_fare_52
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
WHERE fare_amount = 52
GROUP BY rate_code
ORDER BY trips DESC;


-- -----------------------------------------------------------------------------
-- C4: distribución por número de pasajeros, con nulos.
-- Pregunta: ¿cuántos pasajeros lleva cada viaje y cambia el gasto con ese
-- número?
-- Control: la suma de trips, incluida la fila NULL, debe ser 34,796,108.
-- -----------------------------------------------------------------------------

-- [C4]
SELECT
  passenger_count,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(AVG(total_amount), 2) AS avg_total
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY passenger_count
ORDER BY passenger_count NULLS FIRST;


-- -----------------------------------------------------------------------------
-- C5: distribución por proveedor (vendor_id).
-- Pregunta: ¿qué proveedores registran los viajes y con qué gasto promedio?
-- Se muestra el código sin traducir.
-- -----------------------------------------------------------------------------

-- [C5]
SELECT
  vendor_id,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(AVG(total_amount), 2) AS avg_total
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY vendor_id
ORDER BY vendor_id;


-- -----------------------------------------------------------------------------
-- C6a: top 10 de zonas de origen.
-- Pregunta: ¿dónde empiezan la mayoría de los viajes?
-- Se agrega por pickup_location_id, se calcula el porcentaje sobre el total
-- con una ventana y se ordena con RANK. LEFT JOIN conserva los ids sin zona.
-- -----------------------------------------------------------------------------

-- [C6a]
WITH zones AS (
  SELECT DISTINCT zone_id, zone_name, borough
  FROM `bigquery-public-data.new_york_taxi_trips.taxi_zone_geom`
),
by_location AS (
  SELECT pickup_location_id AS location_id, COUNT(*) AS trips, AVG(total_amount) AS avg_total
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY location_id
),
ranked AS (
  SELECT
    RANK() OVER (ORDER BY b.trips DESC) AS trip_rank,
    b.location_id,
    z.zone_name,
    z.borough,
    b.trips,
    100 * b.trips / SUM(b.trips) OVER () AS pct_trips,
    b.avg_total
  FROM by_location AS b
  LEFT JOIN zones AS z ON b.location_id = z.zone_id
)
SELECT
  trip_rank,
  location_id,
  zone_name,
  borough,
  trips,
  ROUND(pct_trips, 2) AS pct_trips,
  ROUND(avg_total, 2) AS avg_total
FROM ranked
WHERE trip_rank <= 10
ORDER BY trip_rank;


-- -----------------------------------------------------------------------------
-- C6b: top 10 de zonas de destino.
-- Pregunta: ¿dónde terminan la mayoría de los viajes?
-- Misma lógica que C6a sobre dropoff_location_id.
-- -----------------------------------------------------------------------------

-- [C6b]
WITH zones AS (
  SELECT DISTINCT zone_id, zone_name, borough
  FROM `bigquery-public-data.new_york_taxi_trips.taxi_zone_geom`
),
by_location AS (
  SELECT dropoff_location_id AS location_id, COUNT(*) AS trips, AVG(total_amount) AS avg_total
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY location_id
),
ranked AS (
  SELECT
    RANK() OVER (ORDER BY b.trips DESC) AS trip_rank,
    b.location_id,
    z.zone_name,
    z.borough,
    b.trips,
    100 * b.trips / SUM(b.trips) OVER () AS pct_trips,
    b.avg_total
  FROM by_location AS b
  LEFT JOIN zones AS z ON b.location_id = z.zone_id
)
SELECT
  trip_rank,
  location_id,
  zone_name,
  borough,
  trips,
  ROUND(pct_trips, 2) AS pct_trips,
  ROUND(avg_total, 2) AS avg_total
FROM ranked
WHERE trip_rank <= 10
ORDER BY trip_rank;


-- -----------------------------------------------------------------------------
-- C6c: ids de ubicación sin zona en taxi_zone_geom.
-- Pregunta: ¿cuántos viajes tienen un origen o destino que no corresponde a
-- ninguna zona? En el diccionario de TLC, 264 y 265 son Unknown y Outside of
-- NYC.
-- LEFT JOIN y z.zone_id IS NULL identifican los ids sin coincidencia.
-- -----------------------------------------------------------------------------

-- [C6c]
WITH zones AS (
  SELECT DISTINCT zone_id
  FROM `bigquery-public-data.new_york_taxi_trips.taxi_zone_geom`
),
unmatched AS (
  SELECT 'pickup' AS side, t.pickup_location_id AS location_id
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt` AS t
  LEFT JOIN zones AS z ON t.pickup_location_id = z.zone_id
  WHERE z.zone_id IS NULL
  UNION ALL
  SELECT 'dropoff' AS side, t.dropoff_location_id AS location_id
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt` AS t
  LEFT JOIN zones AS z ON t.dropoff_location_id = z.zone_id
  WHERE z.zone_id IS NULL
)
SELECT
  side,
  IFNULL(location_id, 'NULL') AS location_id,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / 34796108, 2) AS pct_of_all_trips
FROM unmatched
GROUP BY side, location_id
ORDER BY side DESC, trips DESC;


-- -----------------------------------------------------------------------------
-- C7: viajes por borough de origen.
-- Pregunta: ¿cómo se reparten los viajes entre los boroughs de Nueva York?
-- Los ids sin zona quedan como "Sin zona". Control: la suma de trips debe ser
-- 34,796,108, lo que confirma que la unión con zonas no duplica viajes.
-- -----------------------------------------------------------------------------

-- [C7]
WITH zones AS (
  SELECT DISTINCT zone_id, zone_name, borough
  FROM `bigquery-public-data.new_york_taxi_trips.taxi_zone_geom`
)
SELECT
  IFNULL(z.borough, 'Sin zona') AS pickup_borough,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(AVG(t.total_amount), 2) AS avg_total,
  ROUND(AVG(t.trip_distance), 2) AS avg_distance_mi
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt` AS t
LEFT JOIN zones AS z ON t.pickup_location_id = z.zone_id
GROUP BY pickup_borough
ORDER BY trips DESC;


-- -----------------------------------------------------------------------------
-- C8a: viajes con propina por tipo de pago (prueba de la decisión E4).
-- Pregunta: ¿se registran propinas en los pagos en efectivo?
-- Si el efectivo tiene cerca de 0 % de viajes con tip_amount > 0, las
-- propinas en efectivo no se registran y E4 queda verificada.
-- -----------------------------------------------------------------------------

-- [C8a]
SELECT
  payment_type,
  COUNT(*) AS trips,
  COUNTIF(tip_amount > 0) AS tipped_trips,
  ROUND(100 * COUNTIF(tip_amount > 0) / COUNT(*), 2) AS pct_tipped,
  ROUND(AVG(tip_amount), 2) AS avg_tip
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY payment_type
ORDER BY payment_type;


-- -----------------------------------------------------------------------------
-- C8b: tasa de propina con tarjeta (payment_type '1').
-- Pregunta: ¿qué porcentaje de la tarifa dejan de propina quienes pagan con
-- tarjeta y cuántos no dejan nada?
-- tip_rate = tip_amount / fare_amount, solo con fare_amount > 0. La media es
-- sensible a tarifas muy bajas, por eso se reportan también los percentiles.
-- -----------------------------------------------------------------------------

-- [C8b]
WITH card AS (
  SELECT tip_amount, tip_amount / fare_amount AS tip_rate
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  WHERE payment_type = '1' AND fare_amount > 0
)
SELECT
  COUNT(*) AS card_trips,
  ROUND(100 * AVG(tip_rate), 2) AS avg_tip_rate_pct,
  ROUND(100 * APPROX_QUANTILES(tip_rate, 100)[OFFSET(25)], 2) AS p25_pct,
  ROUND(100 * APPROX_QUANTILES(tip_rate, 100)[OFFSET(50)], 2) AS p50_pct,
  ROUND(100 * APPROX_QUANTILES(tip_rate, 100)[OFFSET(75)], 2) AS p75_pct,
  ROUND(100 * APPROX_QUANTILES(tip_rate, 100)[OFFSET(95)], 2) AS p95_pct,
  ROUND(100 * APPROX_QUANTILES(tip_rate, 100)[OFFSET(99)], 2) AS p99_pct,
  COUNTIF(tip_amount = 0) AS no_tip_trips,
  ROUND(100 * COUNTIF(tip_amount = 0) / COUNT(*), 2) AS pct_no_tip,
  COUNTIF(tip_amount < 0) AS negative_tip_trips
FROM card;
