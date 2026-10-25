-- =============================================================================
-- a_03_eda_descriptiva.sql
-- Propósito : Análisis exploratorio descriptivo de los viajes de 2022: volumen
--             y totales, estadísticas por métrica numérica (media, desviación,
--             extremos y percentiles), velocidad media derivada, distribución
--             por tramos de distancia, tarifa por milla y nulos de
--             passenger_count.
-- Dueño     : Persona A (zona verde).
-- Entradas  : ss2-g16-proyecto2.p2_a_trips.trips_2022_opt (decisión E1;
--             34,796,108 filas, mismo esquema que el contrato).
-- Salidas   : Ninguna tabla. Seis resultados de consulta (D1 a D6).
-- Ejecución : Una consulta por archivo, primero con --dry_run, según
--             conventions.md:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --format=pretty < <archivo>"
-- Evidencia : Proyecto_2/evidencia/07_eda_descriptiva.txt
-- Referencia: odd/tasks/p2-a-eda.md (tarea T2).
-- Nota      : Los percentiles salen de APPROX_QUANTILES(x, 100), que es una
--             aproximación; OFFSET(n) corresponde al percentil n.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- D1: volumen y totales generales.
-- Pregunta: ¿cuántos viajes hay, cuántos días cubren y cuánto suman el ingreso,
-- las tarifas, las propinas y la distancia recorrida?
-- Responde el tamaño del conjunto y sirve de control: trips debe ser
-- 34,796,108. Las sumas se convierten a NUMERIC para mostrarlas sin notación
-- científica.
-- -----------------------------------------------------------------------------

-- [D1]
SELECT
  COUNT(*) AS trips,
  COUNT(DISTINCT pickup_date) AS distinct_days,
  MIN(pickup_date) AS first_day,
  MAX(pickup_date) AS last_day,
  ROUND(COUNT(*) / COUNT(DISTINCT pickup_date), 1) AS avg_trips_per_day,
  ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
  ROUND(CAST(SUM(fare_amount) AS NUMERIC), 2) AS total_fares,
  ROUND(CAST(SUM(tip_amount) AS NUMERIC), 2) AS total_tips,
  ROUND(CAST(SUM(trip_distance) AS NUMERIC), 2) AS total_distance_mi
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`;


-- -----------------------------------------------------------------------------
-- D2: estadísticas descriptivas por métrica numérica.
-- Pregunta: ¿cómo se distribuyen la distancia, la duración, la tarifa, la
-- propina y el total? ¿Qué tan larga es la cola derecha?
-- UNPIVOT convierte las cinco columnas en pares (metric, value) para calcular
-- las mismas agregaciones en un solo GROUP BY y obtener una fila por métrica.
-- Los percentiles p95 y p99 muestran la cola además de la mediana (p50).
-- -----------------------------------------------------------------------------

-- [D2]
WITH metric_values AS (
  SELECT metric, value
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  UNPIVOT (value FOR metric IN (trip_distance, trip_duration_min, fare_amount, tip_amount, total_amount))
),
metric_stats AS (
  SELECT
    metric,
    COUNT(*) AS n,
    AVG(value) AS avg_value,
    STDDEV(value) AS stddev_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    APPROX_QUANTILES(value, 100) AS q
  FROM metric_values
  GROUP BY metric
)
SELECT
  metric,
  n,
  ROUND(avg_value, 2) AS avg,
  ROUND(stddev_value, 2) AS stddev,
  ROUND(min_value, 2) AS min,
  ROUND(q[OFFSET(25)], 2) AS p25,
  ROUND(q[OFFSET(50)], 2) AS p50,
  ROUND(q[OFFSET(75)], 2) AS p75,
  ROUND(q[OFFSET(95)], 2) AS p95,
  ROUND(q[OFFSET(99)], 2) AS p99,
  ROUND(max_value, 2) AS max
FROM metric_stats
ORDER BY CASE metric
  WHEN 'trip_distance' THEN 1
  WHEN 'trip_duration_min' THEN 2
  WHEN 'fare_amount' THEN 3
  WHEN 'tip_amount' THEN 4
  WHEN 'total_amount' THEN 5
END;


-- -----------------------------------------------------------------------------
-- D3: velocidad media derivada (mph).
-- Pregunta: ¿a qué velocidad se mueven los taxis y cuántos viajes registran
-- una velocidad físicamente implausible?
-- speed_mph = trip_distance / (trip_duration_min / 60). Los viajes de menos
-- de 1 minuto quedan fuera del cálculo (IF devuelve NULL y las agregaciones
-- lo ignoran) porque una duración casi nula infla la velocidad. Los viajes con
-- más de 80 mph se cuentan como valores atípicos: se reportan, no se filtran.
-- -----------------------------------------------------------------------------

-- [D3]
WITH trip_speed AS (
  SELECT
    trip_duration_min,
    IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL) AS speed_mph
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
)
SELECT
  COUNT(*) AS trips,
  COUNTIF(trip_duration_min < 1) AS excluded_under_1min,
  COUNT(speed_mph) AS trips_with_speed,
  ROUND(AVG(speed_mph), 2) AS avg_mph,
  ROUND(STDDEV(speed_mph), 2) AS stddev_mph,
  ROUND(APPROX_QUANTILES(speed_mph, 100 IGNORE NULLS)[OFFSET(25)], 2) AS p25_mph,
  ROUND(APPROX_QUANTILES(speed_mph, 100 IGNORE NULLS)[OFFSET(50)], 2) AS p50_mph,
  ROUND(APPROX_QUANTILES(speed_mph, 100 IGNORE NULLS)[OFFSET(75)], 2) AS p75_mph,
  ROUND(APPROX_QUANTILES(speed_mph, 100 IGNORE NULLS)[OFFSET(95)], 2) AS p95_mph,
  ROUND(APPROX_QUANTILES(speed_mph, 100 IGNORE NULLS)[OFFSET(99)], 2) AS p99_mph,
  ROUND(MAX(speed_mph), 2) AS max_mph,
  COUNTIF(speed_mph > 80) AS trips_over_80mph,
  ROUND(100 * COUNTIF(speed_mph > 80) / COUNT(speed_mph), 4) AS pct_over_80mph
FROM trip_speed;


-- -----------------------------------------------------------------------------
-- D4: participación por tramo de distancia.
-- Pregunta: ¿qué proporción de los viajes es corta, media o larga y cuánto
-- cuesta en promedio cada tramo?
-- CASE asigna cada viaje a un tramo de distancia en millas. El porcentaje usa
-- SUM(COUNT(*)) OVER (), una función de ventana sobre el resultado agregado.
-- Control: la suma de trips debe ser 34,796,108.
-- -----------------------------------------------------------------------------

-- [D4]
WITH banded AS (
  SELECT
    CASE
      WHEN trip_distance < 1 THEN '1 [0, 1)'
      WHEN trip_distance < 3 THEN '2 [1, 3)'
      WHEN trip_distance < 5 THEN '3 [3, 5)'
      WHEN trip_distance < 10 THEN '4 [5, 10)'
      WHEN trip_distance < 20 THEN '5 [10, 20)'
      ELSE '6 [20, +)'
    END AS distance_band,
    fare_amount,
    total_amount
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
)
SELECT
  distance_band,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  ROUND(AVG(total_amount), 2) AS avg_total
FROM banded
GROUP BY distance_band
ORDER BY distance_band;


-- -----------------------------------------------------------------------------
-- D5: tarifa por milla según tramo de distancia.
-- Pregunta: ¿cuánto se paga por milla en viajes cortos frente a viajes largos?
-- Responde el efecto del costo fijo: si existe un cargo inicial, la tarifa por
-- milla debe bajar a medida que crece la distancia.
-- fare_per_mile_agg = SUM(fare_amount) / SUM(trip_distance), ponderado por
-- distancia. p50_fare_per_mile es la mediana por viaje; SAFE_DIVIDE devuelve
-- NULL cuando trip_distance = 0 y esos viajes quedan fuera de la mediana.
-- -----------------------------------------------------------------------------

-- [D5]
WITH banded AS (
  SELECT
    CASE
      WHEN trip_distance < 1 THEN '1 [0, 1)'
      WHEN trip_distance < 3 THEN '2 [1, 3)'
      WHEN trip_distance < 5 THEN '3 [3, 5)'
      WHEN trip_distance < 10 THEN '4 [5, 10)'
      WHEN trip_distance < 20 THEN '5 [10, 20)'
      ELSE '6 [20, +)'
    END AS distance_band,
    trip_distance,
    fare_amount,
    SAFE_DIVIDE(fare_amount, trip_distance) AS fare_per_mile
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
)
SELECT
  distance_band,
  COUNT(*) AS trips,
  ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
  ROUND(SUM(fare_amount) / SUM(trip_distance), 2) AS fare_per_mile_agg,
  ROUND(APPROX_QUANTILES(fare_per_mile, 100 IGNORE NULLS)[OFFSET(50)], 2) AS p50_fare_per_mile,
  COUNTIF(trip_distance = 0) AS zero_distance_trips
FROM banded
GROUP BY distance_band
ORDER BY distance_band;


-- -----------------------------------------------------------------------------
-- D6: nulos en passenger_count.
-- Pregunta: ¿cuántos viajes no registran el número de pasajeros y cuántos
-- registran cero?
-- Es contexto para la imputación que hace Persona B en sus features.
-- -----------------------------------------------------------------------------

-- [D6]
SELECT
  COUNT(*) AS trips,
  COUNTIF(passenger_count IS NULL) AS null_passenger_count,
  ROUND(100 * COUNTIF(passenger_count IS NULL) / COUNT(*), 2) AS pct_null,
  COUNTIF(passenger_count = 0) AS zero_passenger_count,
  ROUND(100 * COUNTIF(passenger_count = 0) / COUNT(*), 2) AS pct_zero
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`;
