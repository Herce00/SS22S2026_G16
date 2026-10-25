-- =============================================================================
-- a_06_vistas_eda.sql
-- Propósito : Publicación de las cuatro vistas analíticas v_eda_* en el dataset
--             p2_a_trips para alimentar las visualizaciones exploratorias del
--             tablero (Looker Studio / Google Sheets):
--             1. v_eda_tendencia_diaria: serie temporal diaria con media móvil
--                de 7 días para suavizar la estacionalidad semanal.
--             2. v_eda_hora_dia: matriz bidimensional hora × día de la semana
--                para mapas de calor y perfiles de congestión horaria.
--             3. v_eda_zonas: agregaciones por zona de origen y destino con
--                nombres y boroughs oficiales de NYC, métricas de viaje y rangos.
--             4. v_eda_pagos: caracterización de medios de pago, tasas de
--                propina y desglose del código 0.
-- Dueño     : Persona A (zona verde).
-- Entradas  : ss2-g16-proyecto2.p2_a_trips.trips_2022_opt (decisión E1;
--             34,796,108 filas, tabla optimizada con partición y clustering).
--             bigquery-public-data.new_york_taxi_trips.taxi_zone_geom
--             (decisión E2; deduplicada mediante SELECT DISTINCT).
-- Salidas   : Cuatro vistas en ss2-g16-proyecto2.p2_a_trips:
--             - v_eda_tendencia_diaria (335 filas)
--             - v_eda_hora_dia (168 filas)
--             - v_eda_zonas (264 filas con actividad)
--             - v_eda_pagos (6 filas)
-- Ejecución : cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false < <archivo>"
-- Evidencia : Proyecto_2/evidencia/10_vistas_eda.txt
-- Referencia: odd/tasks/p2-a-eda.md (tarea T5, decisión E5).
-- Notas     : - Las vistas no duplican almacenamiento: se consultan sobre opt
--               aprovechando sus particiones y clustering.
--             - Diciembre contiene 57 viajes del 2022-12-01.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- V1: v_eda_tendencia_diaria.
-- Propósito: Alimenta gráficos de líneas temporales, evolución de ingresos,
-- viajes diarios y la trayectoria suavizada por la media móvil de 7 días.
-- -----------------------------------------------------------------------------

-- [V1]
CREATE OR REPLACE VIEW `ss2-g16-proyecto2.p2_a_trips.v_eda_tendencia_diaria` AS
WITH daily AS (
  SELECT
    pickup_date,
    pickup_month,
    pickup_dow,
    CASE pickup_dow
      WHEN 1 THEN 'Domingo'
      WHEN 2 THEN 'Lunes'
      WHEN 3 THEN 'Martes'
      WHEN 4 THEN 'Miércoles'
      WHEN 5 THEN 'Jueves'
      WHEN 6 THEN 'Viernes'
      WHEN 7 THEN 'Sábado'
    END AS day_name,
    IF(pickup_dow IN (1, 7), 'Fin de semana', 'Día hábil') AS day_type,
    COUNT(*) AS trips,
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
    ROUND(AVG(total_amount), 2) AS avg_total,
    ROUND(AVG(fare_amount), 2) AS avg_fare,
    ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
    ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
    ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_speed_mph
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY pickup_date, pickup_month, pickup_dow, day_name, day_type
)
SELECT
  pickup_date,
  pickup_month,
  pickup_dow,
  day_name,
  day_type,
  trips,
  ROUND(AVG(trips) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS trips_ma7,
  total_revenue,
  ROUND(CAST(AVG(total_revenue) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS NUMERIC), 2) AS revenue_ma7,
  avg_total,
  avg_fare,
  avg_duration_min,
  avg_distance_mi,
  avg_speed_mph
FROM daily;


-- -----------------------------------------------------------------------------
-- V2: v_eda_hora_dia.
-- Propósito: Alimenta visualizaciones de matriz de calor (heatmap 24 × 7),
-- perfiles horarios por día de la semana y análisis de horas punta.
-- -----------------------------------------------------------------------------

-- [V2]
CREATE OR REPLACE VIEW `ss2-g16-proyecto2.p2_a_trips.v_eda_hora_dia` AS
WITH base AS (
  SELECT
    pickup_dow,
    CASE pickup_dow
      WHEN 1 THEN 'Domingo'
      WHEN 2 THEN 'Lunes'
      WHEN 3 THEN 'Martes'
      WHEN 4 THEN 'Miércoles'
      WHEN 5 THEN 'Jueves'
      WHEN 6 THEN 'Viernes'
      WHEN 7 THEN 'Sábado'
    END AS day_name,
    CASE pickup_dow
      WHEN 1 THEN 'Dom'
      WHEN 2 THEN 'Lun'
      WHEN 3 THEN 'Mar'
      WHEN 4 THEN 'Mie'
      WHEN 5 THEN 'Jue'
      WHEN 6 THEN 'Vie'
      WHEN 7 THEN 'Sab'
    END AS dow_abbr,
    pickup_hour,
    IF(pickup_dow IN (1, 7), 'Fin de semana', 'Día hábil') AS day_type,
    COUNT(*) AS trips,
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
    ROUND(AVG(total_amount), 2) AS avg_total,
    ROUND(AVG(fare_amount), 2) AS avg_fare,
    ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
    ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
    ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_speed_mph
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY pickup_dow, day_name, dow_abbr, pickup_hour, day_type
)
SELECT
  pickup_dow,
  day_name,
  dow_abbr,
  pickup_hour,
  day_type,
  trips,
  ROUND(100 * trips / SUM(trips) OVER (PARTITION BY pickup_dow), 2) AS pct_of_day_trips,
  ROUND(100 * trips / SUM(trips) OVER (), 2) AS pct_of_total_trips,
  total_revenue,
  avg_total,
  avg_fare,
  avg_duration_min,
  avg_distance_mi,
  avg_speed_mph,
  RANK() OVER (ORDER BY trips DESC) AS overall_rank,
  RANK() OVER (PARTITION BY pickup_dow ORDER BY trips DESC) AS rank_in_day
FROM base;


-- -----------------------------------------------------------------------------
-- V3: v_eda_zonas.
-- Propósito: Alimenta mapas geoespaciales, gráficos de ranking de zonas más
-- transitadas y distribución de flujos de viaje por borough.
-- Deduplica taxi_zone_geom mediante SELECT DISTINCT (decisión E2).
-- -----------------------------------------------------------------------------

-- [V3]
CREATE OR REPLACE VIEW `ss2-g16-proyecto2.p2_a_trips.v_eda_zonas` AS
WITH zones AS (
  SELECT DISTINCT
    CAST(zone_id AS STRING) AS zone_id,
    zone_name,
    borough
  FROM `bigquery-public-data.new_york_taxi_trips.taxi_zone_geom`
),
pickups AS (
  SELECT
    pickup_location_id,
    COUNT(*) AS pickup_trips,
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS pickup_revenue,
    ROUND(AVG(total_amount), 2) AS avg_pickup_total,
    ROUND(AVG(fare_amount), 2) AS avg_pickup_fare,
    ROUND(AVG(trip_duration_min), 2) AS avg_pickup_duration_min,
    ROUND(AVG(trip_distance), 2) AS avg_pickup_distance_mi,
    ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_pickup_speed_mph
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY pickup_location_id
),
dropoffs AS (
  SELECT
    dropoff_location_id,
    COUNT(*) AS dropoff_trips,
    ROUND(AVG(total_amount), 2) AS avg_dropoff_total,
    ROUND(AVG(trip_duration_min), 2) AS avg_dropoff_duration_min,
    ROUND(AVG(trip_distance), 2) AS avg_dropoff_distance_mi
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY dropoff_location_id
),
combined AS (
  SELECT
    COALESCE(p.pickup_location_id, d.dropoff_location_id) AS location_id,
    IFNULL(p.pickup_trips, 0) AS pickup_trips,
    IFNULL(d.dropoff_trips, 0) AS dropoff_trips,
    p.pickup_revenue,
    p.avg_pickup_total,
    p.avg_pickup_fare,
    p.avg_pickup_duration_min,
    p.avg_pickup_distance_mi,
    p.avg_pickup_speed_mph,
    d.avg_dropoff_total,
    d.avg_dropoff_duration_min,
    d.avg_dropoff_distance_mi
  FROM pickups AS p
  FULL OUTER JOIN dropoffs AS d ON p.pickup_location_id = d.dropoff_location_id
)
SELECT
  c.location_id,
  IFNULL(z.zone_name, CASE c.location_id WHEN '264' THEN 'NV/Desconocido (264)' WHEN '265' THEN 'Fuera de NYC (265)' ELSE CONCAT('Sin zona (', c.location_id, ')') END) AS zone_name,
  IFNULL(z.borough, 'Sin zona') AS borough,
  c.pickup_trips,
  ROUND(100 * c.pickup_trips / SUM(c.pickup_trips) OVER (), 2) AS pct_pickup_trips,
  c.dropoff_trips,
  ROUND(100 * c.dropoff_trips / SUM(c.dropoff_trips) OVER (), 2) AS pct_dropoff_trips,
  c.pickup_trips + c.dropoff_trips AS total_trips,
  c.pickup_revenue,
  c.avg_pickup_total,
  c.avg_pickup_fare,
  c.avg_pickup_duration_min,
  c.avg_pickup_distance_mi,
  c.avg_pickup_speed_mph,
  c.avg_dropoff_total,
  c.avg_dropoff_duration_min,
  c.avg_dropoff_distance_mi,
  RANK() OVER (ORDER BY c.pickup_trips DESC) AS pickup_rank,
  RANK() OVER (ORDER BY c.dropoff_trips DESC) AS dropoff_rank
FROM combined AS c
LEFT JOIN zones AS z ON c.location_id = z.zone_id;


-- -----------------------------------------------------------------------------
-- V4: v_eda_pagos.
-- Propósito: Alimenta visualizaciones de participación por tipo de pago,
-- tasa de propina, comparación entre tarjeta y efectivo, y métricas del código 0.
-- -----------------------------------------------------------------------------

-- [V4]
CREATE OR REPLACE VIEW `ss2-g16-proyecto2.p2_a_trips.v_eda_pagos` AS
WITH base AS (
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
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
    ROUND(AVG(total_amount), 2) AS avg_total,
    ROUND(AVG(fare_amount), 2) AS avg_fare,
    ROUND(AVG(tip_amount), 2) AS avg_tip,
    COUNTIF(tip_amount > 0) AS tipped_trips,
    ROUND(100 * COUNTIF(tip_amount > 0) / COUNT(*), 2) AS pct_tipped,
    ROUND(100 * AVG(IF(fare_amount > 0, tip_amount / fare_amount, NULL)), 2) AS avg_tip_rate_pct,
    ROUND(100 * APPROX_QUANTILES(IF(fare_amount > 0, tip_amount / fare_amount, NULL), 100 IGNORE NULLS)[OFFSET(50)], 2) AS p50_tip_rate_pct,
    ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
    ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
    ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_speed_mph
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY payment_type, payment_label
)
SELECT
  payment_type,
  payment_label,
  trips,
  ROUND(100 * trips / SUM(trips) OVER (), 2) AS pct_trips,
  total_revenue,
  avg_total,
  avg_fare,
  avg_tip,
  tipped_trips,
  pct_tipped,
  avg_tip_rate_pct,
  p50_tip_rate_pct,
  avg_distance_mi,
  avg_duration_min,
  avg_speed_mph
FROM base;
