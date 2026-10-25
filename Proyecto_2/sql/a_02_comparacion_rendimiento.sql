-- =============================================================================
-- a_02_comparacion_rendimiento.sql
-- Propósito : Comparar el rendimiento de la misma consulta lógica sobre tres
--             fuentes: la tabla pública (sin partición ni clustering),
--             trips_2022_std (copia sin partición ni clustering) y
--             trips_2022_opt (partición diaria y clustering por ubicaciones).
-- Dueño     : Persona A (zona verde).
-- Entradas  : bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022
--             ss2-g16-proyecto2.p2_a_trips.trips_2022_std
--             ss2-g16-proyecto2.p2_a_trips.trips_2022_opt
--             `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
-- Salidas   : Ninguna tabla. Resultados y métricas de los 12 trabajos.
-- Método    : Decisión O5.
--             1. Cada consulta (Q1 a Q4) se escribe tres veces, una por fuente,
--                con la misma lógica; solo cambia la tabla del FROM.
--             2. Cada consulta se ejecuta por separado con --nouse_cache y un
--                --job_id determinista p2_cmp_<q>_<fuente>_<unix-ts>.
--             3. Las métricas reales (bytes procesados, bytes facturados, slot
--                ms y duración) se leen de JOBS_BY_USER, bloque final.
--             4. El dry run registra los bytes estimados. En tablas con
--                clustering el dry run es una cota superior ("upper bound");
--                la poda por clustering se confirma en los bytes reales.
-- Ejecución : Una consulta por archivo, según conventions.md:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --nouse_cache --format=pretty
--               --job_id=p2_cmp_q1_opt_<ts> < <archivo>"
-- Evidencia : Proyecto_2/evidencia/05_comparacion_rendimiento.txt
-- Referencia: odd/tasks/p2-a-optimizacion.md (decisión O5, criterio T3).
-- Nota      : Los resultados de std y opt deben ser idénticos (mismos datos).
--             La tabla pública da otras cifras porque no aplica los 7 filtros
--             de limpieza del contrato.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Q1: poda por partición.
-- Viajes diarios y tarifa promedio de una semana (2022-03-07 a 2022-03-13).
-- El filtro va directo sobre pickup_datetime con literales TIMESTAMP; en una
-- tabla particionada por DATE(pickup_datetime) ese filtro poda particiones.
-- Efecto esperado: opt lee solo 7 de 335 particiones y queda muy por debajo de
-- std; std y la tabla pública leen todas las filas.
-- -----------------------------------------------------------------------------

-- [Q1-public]
SELECT DATE(pickup_datetime) AS trip_date, COUNT(*) AS trips, ROUND(AVG(fare_amount), 2) AS avg_fare
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
WHERE pickup_datetime >= TIMESTAMP '2022-03-07' AND pickup_datetime < TIMESTAMP '2022-03-14'
GROUP BY trip_date
ORDER BY trip_date;

-- [Q1-std]
SELECT DATE(pickup_datetime) AS trip_date, COUNT(*) AS trips, ROUND(AVG(fare_amount), 2) AS avg_fare
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_std`
WHERE pickup_datetime >= TIMESTAMP '2022-03-07' AND pickup_datetime < TIMESTAMP '2022-03-14'
GROUP BY trip_date
ORDER BY trip_date;

-- [Q1-opt]
SELECT DATE(pickup_datetime) AS trip_date, COUNT(*) AS trips, ROUND(AVG(fare_amount), 2) AS avg_fare
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
WHERE pickup_datetime >= TIMESTAMP '2022-03-07' AND pickup_datetime < TIMESTAMP '2022-03-14'
GROUP BY trip_date
ORDER BY trip_date;


-- -----------------------------------------------------------------------------
-- Q2: poda por clustering.
-- Viajes mensuales y total promedio con origen en la zona 132 (JFK) durante
-- todo 2022. El rango de fechas cubre todas las particiones, así que no hay
-- poda por partición; cualquier reducción en opt viene del clustering por
-- pickup_location_id.
-- Efecto esperado: opt por debajo de std en bytes reales.
-- -----------------------------------------------------------------------------

-- [Q2-public]
SELECT EXTRACT(MONTH FROM pickup_datetime) AS trip_month, COUNT(*) AS trips, ROUND(AVG(total_amount), 2) AS avg_total
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
WHERE pickup_location_id = '132'
  AND pickup_datetime >= TIMESTAMP '2022-01-01' AND pickup_datetime < TIMESTAMP '2023-01-01'
GROUP BY trip_month
ORDER BY trip_month;

-- [Q2-std]
SELECT EXTRACT(MONTH FROM pickup_datetime) AS trip_month, COUNT(*) AS trips, ROUND(AVG(total_amount), 2) AS avg_total
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_std`
WHERE pickup_location_id = '132'
  AND pickup_datetime >= TIMESTAMP '2022-01-01' AND pickup_datetime < TIMESTAMP '2023-01-01'
GROUP BY trip_month
ORDER BY trip_month;

-- [Q2-opt]
SELECT EXTRACT(MONTH FROM pickup_datetime) AS trip_month, COUNT(*) AS trips, ROUND(AVG(total_amount), 2) AS avg_total
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
WHERE pickup_location_id = '132'
  AND pickup_datetime >= TIMESTAMP '2022-01-01' AND pickup_datetime < TIMESTAMP '2023-01-01'
GROUP BY trip_month
ORDER BY trip_month;


-- -----------------------------------------------------------------------------
-- Q3: poda por partición y por clustering a la vez.
-- Top 10 de zonas de destino por número de viajes con origen en la zona 161
-- durante junio de 2022.
-- Efecto esperado: la mayor reducción relativa, porque opt lee solo las
-- particiones de junio y, dentro de ellas, solo los bloques de la zona 161.
-- -----------------------------------------------------------------------------

-- [Q3-public]
SELECT dropoff_location_id, COUNT(*) AS trips
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
WHERE pickup_location_id = '161'
  AND pickup_datetime >= TIMESTAMP '2022-06-01' AND pickup_datetime < TIMESTAMP '2022-07-01'
GROUP BY dropoff_location_id
ORDER BY trips DESC, dropoff_location_id
LIMIT 10;

-- [Q3-std]
SELECT dropoff_location_id, COUNT(*) AS trips
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_std`
WHERE pickup_location_id = '161'
  AND pickup_datetime >= TIMESTAMP '2022-06-01' AND pickup_datetime < TIMESTAMP '2022-07-01'
GROUP BY dropoff_location_id
ORDER BY trips DESC, dropoff_location_id
LIMIT 10;

-- [Q3-opt]
SELECT dropoff_location_id, COUNT(*) AS trips
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
WHERE pickup_location_id = '161'
  AND pickup_datetime >= TIMESTAMP '2022-06-01' AND pickup_datetime < TIMESTAMP '2022-07-01'
GROUP BY dropoff_location_id
ORDER BY trips DESC, dropoff_location_id
LIMIT 10;


-- -----------------------------------------------------------------------------
-- Q4: control sin filtro selectivo.
-- Total promedio por tipo de pago en todo el año, sin WHERE. No filtra por
-- la columna de partición ni por las de clustering.
-- Efecto esperado: poca o ninguna reducción de opt frente a std. Se incluye
-- para no presentar solo los casos favorables.
-- -----------------------------------------------------------------------------

-- [Q4-public]
SELECT payment_type, COUNT(*) AS trips, ROUND(AVG(total_amount), 2) AS avg_total
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
GROUP BY payment_type
ORDER BY payment_type;

-- [Q4-std]
SELECT payment_type, COUNT(*) AS trips, ROUND(AVG(total_amount), 2) AS avg_total
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_std`
GROUP BY payment_type
ORDER BY payment_type;

-- [Q4-opt]
SELECT payment_type, COUNT(*) AS trips, ROUND(AVG(total_amount), 2) AS avg_total
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY payment_type
ORDER BY payment_type;


-- -----------------------------------------------------------------------------
-- Bloque final: métricas reales de los 12 trabajos.
-- Los job_id siguen el patrón p2_cmp_q<n>_<fuente>_<unix-ts>, donde <unix-ts>
-- es la marca de tiempo común de la corrida (date +%s antes de ejecutar).
-- Reemplazar 1792951405 por la marca de tiempo de la corrida que se quiera
-- medir; también puede listarse con `bq ls -j -n 20`.
-- cache_hit debe ser false en los 12 trabajos.
-- -----------------------------------------------------------------------------

-- [Q-metricas]
SELECT
  job_id,
  total_bytes_processed,
  total_bytes_billed,
  total_slot_ms,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) AS elapsed_ms,
  cache_hit
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND job_id LIKE 'p2_cmp_q%_1792951405'
ORDER BY job_id;
