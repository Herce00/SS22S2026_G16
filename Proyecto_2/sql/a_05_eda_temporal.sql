-- =============================================================================
-- a_05_eda_temporal.sql
-- Propósito : Análisis exploratorio de los patrones temporales de los viajes de
--             2022: distribución por hora del día, día de la semana, evolución
--             mensual con LAG y cálculo de variaciones, matriz pivot hora × día,
--             ranking de horas pico, tendencia diaria con media móvil de 7 días,
--             comparativa de días hábiles vs. fin de semana, y comportamiento de
--             la propina con tarjeta por hora.
-- Dueño     : Persona A (zona verde).
-- Entradas  : ss2-g16-proyecto2.p2_a_trips.trips_2022_opt (decisión E1;
--             34,796,108 filas, mismo esquema que el contrato).
-- Salidas   : Ninguna tabla. Resultados de consulta T1 a T7.
-- Ejecución : Una consulta por archivo, primero con --dry_run, según
--             conventions.md:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --format=pretty < <archivo>"
-- Evidencia : Proyecto_2/evidencia/09_eda_temporal.txt
-- Referencia: odd/tasks/p2-a-eda.md (tarea T4, decisión E4).
-- Notas     : - Diciembre no representa un mes completo: contiene únicamente
--               57 viajes del 2022-12-01 incluidos en la ingesta pública de
--               noviembre. Se analiza y se aísla explícitamente.
--             - pickup_dow en BigQuery sigue el estándar de DAYOFWEEK:
--               1 = Domingo, 2 = Lunes, ..., 7 = Sábado.
--             - La media móvil de 7 días usa ROWS BETWEEN 6 PRECEDING AND
--               CURRENT ROW para eliminar la oscilación intrínseca semanal.
--             - El análisis de propinas usa exclusivamente pagos con tarjeta
--               (payment_type = '1'), conforme a la decisión verificada E4.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- T1: distribución por hora del día.
-- Pregunta: ¿cómo varían la demanda, los ingresos, la duración, la distancia y
-- la velocidad media a lo largo de las 24 horas del día?
-- speed_mph excluye viajes de menos de 1 minuto para evitar distorsiones.
-- Control: la suma de trips debe ser 34,796,108.
-- -----------------------------------------------------------------------------

-- [T1]
SELECT
  pickup_hour,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  ROUND(AVG(total_amount), 2) AS avg_total,
  ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
  ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
  ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_speed_mph
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY pickup_hour
ORDER BY pickup_hour;


-- -----------------------------------------------------------------------------
-- T2: distribución por día de la semana.
-- Pregunta: ¿cuáles son los días con mayor demanda semanal y cómo varían el
-- gasto, la duración y la velocidad entre días laborales y fin de semana?
-- Se computan días distintos por día de la semana para normalizar viajes/día.
-- Control: la suma de trips debe ser 34,796,108 y distinct_days sumar 335.
-- -----------------------------------------------------------------------------

-- [T2]
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
  COUNT(DISTINCT pickup_date) AS distinct_days,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(COUNT(*) / COUNT(DISTINCT pickup_date), 1) AS avg_trips_per_day,
  ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
  ROUND(AVG(total_amount), 2) AS avg_total,
  ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
  ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
  ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_speed_mph
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY pickup_dow, day_name
ORDER BY CASE pickup_dow
  WHEN 2 THEN 1 -- Lunes
  WHEN 3 THEN 2 -- Martes
  WHEN 4 THEN 3 -- Miércoles
  WHEN 5 THEN 4 -- Jueves
  WHEN 6 THEN 5 -- Viernes
  WHEN 7 THEN 6 -- Sábado
  WHEN 1 THEN 7 -- Domingo
END;


-- -----------------------------------------------------------------------------
-- T3: evolución mensual con LAG y variación intermensual.
-- Pregunta: ¿cómo evoluciona el volumen mensual de viajes e ingresos y cuál es
-- la tasa de crecimiento mes a mes?
-- LAG calcula el volumen del mes precedente. Diciembre aparece con solo 57
-- viajes del 2022-12-01.
-- Control: la suma de trips debe ser 34,796,108.
-- -----------------------------------------------------------------------------

-- [T3]
SELECT
  pickup_month,
  CASE pickup_month
    WHEN 1 THEN 'Enero'
    WHEN 2 THEN 'Febrero'
    WHEN 3 THEN 'Marzo'
    WHEN 4 THEN 'Abril'
    WHEN 5 THEN 'Mayo'
    WHEN 6 THEN 'Junio'
    WHEN 7 THEN 'Julio'
    WHEN 8 THEN 'Agosto'
    WHEN 9 THEN 'Septiembre'
    WHEN 10 THEN 'Octubre'
    WHEN 11 THEN 'Noviembre'
    WHEN 12 THEN 'Diciembre (1 día)'
  END AS month_name,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  LAG(COUNT(*)) OVER (ORDER BY pickup_month) AS prev_month_trips,
  COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY pickup_month) AS abs_diff,
  ROUND(100 * (COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY pickup_month)) / LAG(COUNT(*)) OVER (ORDER BY pickup_month), 2) AS pct_growth,
  ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
  ROUND(AVG(total_amount), 2) AS avg_total,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
  ROUND(AVG(trip_distance), 2) AS avg_distance_mi
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY pickup_month
ORDER BY pickup_month;


-- -----------------------------------------------------------------------------
-- T4a: matriz pivot hora × día de la semana.
-- Pregunta: ¿cuál es la distribución espacial y temporal de la demanda en la
-- cuadrícula de 24 horas por 7 días?
-- PIVOT proyecta las 24 horas como filas y los 7 días ordenados como columnas.
-- -----------------------------------------------------------------------------

-- [T4a]
WITH base AS (
  SELECT
    pickup_hour,
    CASE pickup_dow
      WHEN 1 THEN 'Dom'
      WHEN 2 THEN 'Lun'
      WHEN 3 THEN 'Mar'
      WHEN 4 THEN 'Mie'
      WHEN 5 THEN 'Jue'
      WHEN 6 THEN 'Vie'
      WHEN 7 THEN 'Sab'
    END AS dow_abbr,
    COUNT(*) AS trips
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY pickup_hour, dow_abbr
)
SELECT * FROM base
PIVOT (
  SUM(trips) FOR dow_abbr IN ('Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom')
)
ORDER BY pickup_hour;


-- -----------------------------------------------------------------------------
-- T4b: ranking de combinaciones hora × día (top 20 general y hora pico por día).
-- Pregunta: ¿cuáles son los 20 momentos de mayor demanda en la semana y a qué
-- hora se produce el pico específico de cada día?
-- RANK() calcula la posición global (overall_rank) y dentro del día (rank_in_day).
-- -----------------------------------------------------------------------------

-- [T4b]
WITH hora_dia AS (
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
    pickup_hour,
    COUNT(*) AS trips,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY pickup_dow), 2) AS pct_of_day,
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
    ROUND(AVG(total_amount), 2) AS avg_total,
    ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_speed_mph,
    RANK() OVER (ORDER BY COUNT(*) DESC) AS overall_rank,
    RANK() OVER (PARTITION BY pickup_dow ORDER BY COUNT(*) DESC) AS rank_in_day
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY pickup_dow, day_name, pickup_hour
)
SELECT
  overall_rank,
  rank_in_day,
  pickup_dow,
  day_name,
  pickup_hour,
  trips,
  pct_of_day,
  total_revenue,
  avg_total,
  avg_speed_mph
FROM hora_dia
WHERE overall_rank <= 20 OR rank_in_day = 1
ORDER BY overall_rank;


-- -----------------------------------------------------------------------------
-- T5a: días extremos de demanda (top 5 mayor y top 5 menor).
-- Pregunta: ¿cuáles fueron los días atípicos de máxima y mínima actividad en el
-- año y qué factores contextuales o climáticos los explican?
-- -----------------------------------------------------------------------------

-- [T5a]
WITH daily AS (
  SELECT
    pickup_date,
    CASE EXTRACT(DAYOFWEEK FROM pickup_date)
      WHEN 1 THEN 'Domingo'
      WHEN 2 THEN 'Lunes'
      WHEN 3 THEN 'Martes'
      WHEN 4 THEN 'Miércoles'
      WHEN 5 THEN 'Jueves'
      WHEN 6 THEN 'Viernes'
      WHEN 7 THEN 'Sábado'
    END AS day_name,
    COUNT(*) AS trips,
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY pickup_date, day_name
),
daily_ma AS (
  SELECT
    pickup_date,
    day_name,
    trips,
    ROUND(AVG(trips) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS trips_ma7,
    total_revenue,
    RANK() OVER (ORDER BY trips DESC) AS rank_highest,
    RANK() OVER (ORDER BY trips ASC) AS rank_lowest
  FROM daily
)
SELECT 'Top 5 mayor demanda' AS category, rank_highest AS rank_pos, pickup_date, day_name, trips, trips_ma7, total_revenue
FROM daily_ma
WHERE rank_highest <= 5
UNION ALL
SELECT 'Top 5 menor demanda' AS category, rank_lowest AS rank_pos, pickup_date, day_name, trips, trips_ma7, total_revenue
FROM daily_ma
WHERE rank_lowest <= 5 AND pickup_date != '2022-12-01' -- Excluye dic (1 día aislado)
ORDER BY category DESC, rank_pos;


-- -----------------------------------------------------------------------------
-- T5b: tendencia diaria con media móvil de 7 días (muestra de serie).
-- Pregunta: ¿cómo suaviza la media móvil de 7 días la estacionalidad cíclica
-- semanal de la serie diaria?
-- Se extraen las primeras 2 semanas de cada trimestre para ilustrar la
-- trayectoria anual sin saturar el reporte textual.
-- -----------------------------------------------------------------------------

-- [T5b]
WITH daily AS (
  SELECT
    pickup_date,
    CASE EXTRACT(DAYOFWEEK FROM pickup_date)
      WHEN 1 THEN 'Domingo'
      WHEN 2 THEN 'Lunes'
      WHEN 3 THEN 'Martes'
      WHEN 4 THEN 'Miércoles'
      WHEN 5 THEN 'Jueves'
      WHEN 6 THEN 'Viernes'
      WHEN 7 THEN 'Sábado'
    END AS day_name,
    COUNT(*) AS trips,
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  GROUP BY pickup_date, day_name
),
daily_ma AS (
  SELECT
    pickup_date,
    day_name,
    trips,
    ROUND(AVG(trips) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS trips_ma7,
    total_revenue,
    ROUND(CAST(AVG(total_revenue) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS NUMERIC), 2) AS revenue_ma7
  FROM daily
)
SELECT *
FROM daily_ma
WHERE (pickup_date BETWEEN '2022-01-01' AND '2022-01-14')
   OR (pickup_date BETWEEN '2022-04-01' AND '2022-04-14')
   OR (pickup_date BETWEEN '2022-07-01' AND '2022-07-14')
   OR (pickup_date BETWEEN '2022-10-01' AND '2022-10-14')
   OR (pickup_date BETWEEN '2022-11-24' AND '2022-12-01')
ORDER BY pickup_date;


-- -----------------------------------------------------------------------------
-- T6: comparación de fin de semana vs. día hábil.
-- Pregunta: ¿en qué difieren los patrones de demanda, duración, distancia,
-- velocidad media y costo entre días laborales y de fin de semana?
-- Fin de semana = Sábado (7) y Domingo (1). Día hábil = Lunes (2) a Viernes (6).
-- Control: suma de trips = 34,796,108 y distinct_days = 335.
-- -----------------------------------------------------------------------------

-- [T6]
SELECT
  CASE
    WHEN pickup_dow IN (1, 7) THEN 'Fin de semana'
    ELSE 'Día hábil'
  END AS day_type,
  COUNT(DISTINCT pickup_date) AS distinct_days,
  COUNT(*) AS trips,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_trips,
  ROUND(COUNT(*) / COUNT(DISTINCT pickup_date), 1) AS avg_trips_per_day,
  ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_revenue,
  ROUND(AVG(total_amount), 2) AS avg_total,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  ROUND(AVG(trip_duration_min), 2) AS avg_duration_min,
  ROUND(AVG(trip_distance), 2) AS avg_distance_mi,
  ROUND(AVG(IF(trip_duration_min >= 1, trip_distance / (trip_duration_min / 60), NULL)), 2) AS avg_speed_mph
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
GROUP BY day_type
ORDER BY day_type;


-- -----------------------------------------------------------------------------
-- T7: tasa de propina con tarjeta por hora (decisión E4).
-- Pregunta: ¿varía la generosidad y el porcentaje de propina según la hora del
-- día en pagos con tarjeta?
-- tip_rate = tip_amount / fare_amount sobre payment_type = '1' y fare > 0.
-- Control: suma de card_trips debe ser 26,703,778.
-- -----------------------------------------------------------------------------

-- [T7]
WITH card_hourly AS (
  SELECT
    pickup_hour,
    fare_amount,
    tip_amount,
    tip_amount / fare_amount AS tip_rate
  FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
  WHERE payment_type = '1' AND fare_amount > 0
)
SELECT
  pickup_hour,
  COUNT(*) AS card_trips,
  ROUND(AVG(fare_amount), 2) AS avg_fare,
  ROUND(AVG(tip_amount), 2) AS avg_tip,
  ROUND(100 * AVG(tip_rate), 2) AS avg_tip_rate_pct,
  ROUND(100 * APPROX_QUANTILES(tip_rate, 100)[OFFSET(50)], 2) AS p50_tip_rate_pct,
  COUNTIF(tip_amount = 0) AS no_tip_trips,
  ROUND(100 * COUNTIF(tip_amount = 0) / COUNT(*), 2) AS pct_no_tip
FROM card_hourly
GROUP BY pickup_hour
ORDER BY pickup_hour;
