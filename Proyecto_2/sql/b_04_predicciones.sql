-- =============================================================================
-- b_04_predicciones.sql
-- Propósito : Ejecutar ML.PREDICT sobre los "nuevos registros" (noviembre,
--             split_set = 'new') con los modelos de T3, guardar las
--             predicciones en tablas pred_*, validarlas contra las métricas de
--             T4 y resumir valores reales frente a predichos por día y por
--             borough. Publica la vista diaria v_ml_pred_diaria para el
--             tablero de B.
-- Dueño     : Persona A (decisión D8 del steering; ruta B del flujo).
-- Entradas  : ss2-g16-proyecto2.p2_b_ml.features_trips (b_01_features.sql;
--             split 'new' = 222,890 filas, 172,626 con tarjeta)
--             ss2-g16-proyecto2.p2_b_ml.m_fare_linreg (M-1)
--             ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd (M-2)
--             ss2-g16-proyecto2.p2_b_ml.m_tip_logreg (M-3)
--             (b_02_modelos.sql)
--             ss2-g16-proyecto2.p2_contract.v_trips_clean (solo trip_id y
--             pickup_date; features_trips no tiene columna de fecha)
-- Salidas   : ss2-g16-proyecto2.p2_b_ml.pred_fare_nov
--             ss2-g16-proyecto2.p2_b_ml.pred_tip_nov
--             ss2-g16-proyecto2.p2_b_ml.v_ml_pred_diaria
--             Resultados de consulta P3a a P3c, P4a a P4c y P5b.
-- Ejecución : Un bloque por archivo, primero con --dry_run, según
--             conventions.md:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --format=pretty < <archivo>"
-- Evidencia : Proyecto_2/evidencia/14_predicciones.txt
-- Referencia: odd/tasks/p2-a-bqml.md (tarea T5, decisiones M1 a M4).
-- Notas     : - Cada ML.PREDICT recibe la misma lista explícita de 11
--               features de M2. trip_id, la etiqueta real y las columnas de
--               reporte pasan como columnas de paso: ML.PREDICT las devuelve
--               sin usarlas, porque el modelo solo lee las features con las
--               que se entrenó.
--             - Las tablas guardan las predicciones de M-1 y M-2. El modelo
--               seleccionado para producción es M-2 (13_evaluacion.txt);
--               M-1 se conserva para la comparación de al menos 2 modelos que
--               pide el enunciado.
--             - El split 'new' incluye las filas del 2022-12-01 que vienen en
--               el archivo de noviembre (V1 de 11_features.txt). Es un día
--               parcial: las salidas lo marcan con is_partial_day.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- P1: predicciones de tarifa de M-1 y M-2 sobre noviembre.
-- Pregunta: ¿qué tarifa predice cada modelo de regresión para cada viaje de
-- los nuevos registros, y con qué error absoluto?
-- - Dos ML.PREDICT sobre el mismo conjunto, unidos por trip_id (único en el
--   contrato, 03_contrato_validaciones.txt).
-- - pickup_date sale de v_trips_clean. El filtro pickup_date >= 2022-11-01
--   equivale a pickup_month >= 11 (el split 'new') dentro de 2022 y deja que
--   BigQuery lea solo las particiones de noviembre y del 2022-12-01 de
--   trips_2022_opt.
-- - pickup_hour vuelve a INT64: en features_trips es STRING para que BQML lo
--   trate como categoría (b_01_features.sql), pero el tablero lo ordena como
--   número.
-- Resultado esperado: 222,890 filas, una por viaje del split 'new'.
-- -----------------------------------------------------------------------------

-- [P1]
CREATE OR REPLACE TABLE `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov` AS
WITH m1 AS (
  SELECT
    trip_id,
    pickup_hour,
    pickup_borough,
    trip_distance,
    fare_amount,
    predicted_fare_amount AS pred_fare_m1
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`, (
    SELECT
      trip_id, pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'new'
  ))
),
m2 AS (
  SELECT
    trip_id,
    predicted_fare_amount AS pred_fare_m2
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`, (
    SELECT
      trip_id, pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'new'
  ))
),
dates AS (
  SELECT trip_id, pickup_date
  FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`
  WHERE pickup_date >= '2022-11-01'
)
SELECT
  m1.trip_id,
  d.pickup_date,
  CAST(m1.pickup_hour AS INT64) AS pickup_hour,
  m1.pickup_borough,
  m1.trip_distance,
  m1.fare_amount AS fare_actual,
  m1.pred_fare_m1,
  m2.pred_fare_m2,
  ABS(m1.fare_amount - m1.pred_fare_m1) AS abs_err_m1,
  ABS(m1.fare_amount - m2.pred_fare_m2) AS abs_err_m2
FROM m1
JOIN m2
  ON m2.trip_id = m1.trip_id
JOIN dates AS d
  ON d.trip_id = m1.trip_id;


-- -----------------------------------------------------------------------------
-- P2: predicciones de propina alta de M-3 sobre noviembre.
-- Pregunta: ¿qué probabilidad de propina alta asigna la logística a cada
-- viaje con tarjeta de los nuevos registros?
-- - Solo pagos con tarjeta: is_high_tip IS NOT NULL (decisión M3).
-- - prob_high_tip es la probabilidad de la clase TRUE, tomada del arreglo
--   predicted_is_high_tip_probs (misma extracción que E4c de
--   b_03_evaluacion.sql).
-- - pred_is_high_tip es la clase que devuelve ML.PREDICT con su umbral por
--   defecto (0.5); P3c lo comprueba contra prob_high_tip.
-- Resultado esperado: 172,626 filas (card_rows de 'new', V6 de
-- 11_features.txt).
-- -----------------------------------------------------------------------------

-- [P2]
CREATE OR REPLACE TABLE `ss2-g16-proyecto2.p2_b_ml.pred_tip_nov` AS
WITH m3 AS (
  SELECT
    trip_id,
    pickup_hour,
    pickup_borough,
    is_high_tip,
    predicted_is_high_tip,
    (
      SELECT p.prob FROM UNNEST(predicted_is_high_tip_probs) AS p WHERE p.label
    ) AS prob_high_tip
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
    SELECT
      trip_id, pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, is_high_tip
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'new'
      AND is_high_tip IS NOT NULL
  ))
),
dates AS (
  SELECT trip_id, pickup_date
  FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean`
  WHERE pickup_date >= '2022-11-01'
)
SELECT
  m3.trip_id,
  d.pickup_date,
  CAST(m3.pickup_hour AS INT64) AS pickup_hour,
  m3.pickup_borough,
  m3.is_high_tip AS is_high_tip_actual,
  m3.prob_high_tip,
  m3.predicted_is_high_tip AS pred_is_high_tip
FROM m3
JOIN dates AS d
  ON d.trip_id = m3.trip_id;


-- -----------------------------------------------------------------------------
-- P3a: filas, nulos y rango de fechas de las tablas de predicción.
-- Pregunta: ¿las tablas cubren todo el split 'new' sin perder filas en los
-- joins y sin predicciones nulas?
-- Resultado esperado: pred_fare_nov con 222,890 filas y pred_tip_nov con
-- 172,626 (V1 y V6 de 11_features.txt), trip_id único, 0 nulos en
-- predicciones y fechas, y fechas entre 2022-11-01 y 2022-12-01.
-- -----------------------------------------------------------------------------

-- [P3a]
SELECT
  'pred_fare_nov' AS table_name,
  COUNT(*) AS n_rows,
  COUNT(DISTINCT trip_id) AS n_trip_ids,
  COUNTIF(pred_fare_m1 IS NULL) + COUNTIF(pred_fare_m2 IS NULL) AS null_predictions,
  COUNTIF(pickup_date IS NULL) AS null_dates,
  MIN(pickup_date) AS min_date,
  MAX(pickup_date) AS max_date,
  COUNTIF(pickup_date = '2022-12-01') AS rows_2022_12_01
FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov`
UNION ALL
SELECT
  'pred_tip_nov' AS table_name,
  COUNT(*) AS n_rows,
  COUNT(DISTINCT trip_id) AS n_trip_ids,
  COUNTIF(prob_high_tip IS NULL) + COUNTIF(pred_is_high_tip IS NULL) AS null_predictions,
  COUNTIF(pickup_date IS NULL) AS null_dates,
  MIN(pickup_date) AS min_date,
  MAX(pickup_date) AS max_date,
  COUNTIF(pickup_date = '2022-12-01') AS rows_2022_12_01
FROM `ss2-g16-proyecto2.p2_b_ml.pred_tip_nov`
ORDER BY table_name;


-- -----------------------------------------------------------------------------
-- P3b: RMSE, MAE y R² recalculados desde pred_fare_nov.
-- Pregunta: ¿las predicciones guardadas reproducen las métricas de noviembre
-- de T4?
-- R² = 1 - SSE / SST, con SST respecto de la media de fare_actual en
-- noviembre (mismo método que E7a de b_03_evaluacion.sql).
-- Resultado esperado (E5a de 13_evaluacion.txt): M-1 con RMSE 15.27, MAE
-- 2.04 y R² -0.299; M-2 con RMSE 4.24, MAE 2.55 y R² 0.900.
-- -----------------------------------------------------------------------------

-- [P3b]
WITH stats AS (
  SELECT AVG(fare_actual) AS mean_fare
  FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov`
)
SELECT
  'm_fare_linreg' AS model,
  COUNT(*) AS n_rows,
  SQRT(AVG(POW(p.fare_actual - p.pred_fare_m1, 2))) AS rmse,
  AVG(p.abs_err_m1) AS mae,
  1 - SUM(POW(p.fare_actual - p.pred_fare_m1, 2)) / SUM(POW(p.fare_actual - s.mean_fare, 2)) AS r2
FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov` AS p
CROSS JOIN stats AS s
UNION ALL
SELECT
  'm_fare_linreg_gd' AS model,
  COUNT(*) AS n_rows,
  SQRT(AVG(POW(p.fare_actual - p.pred_fare_m2, 2))) AS rmse,
  AVG(p.abs_err_m2) AS mae,
  1 - SUM(POW(p.fare_actual - p.pred_fare_m2, 2)) / SUM(POW(p.fare_actual - s.mean_fare, 2)) AS r2
FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov` AS p
CROSS JOIN stats AS s
ORDER BY model;


-- -----------------------------------------------------------------------------
-- P3c: exactitud, precisión y recall recalculados desde pred_tip_nov.
-- Pregunta: ¿la clase guardada reproduce las métricas de noviembre de T4, y
-- corresponde al umbral 0.5 sobre prob_high_tip?
-- Resultado esperado (E5b de 13_evaluacion.txt): exactitud 0.6675,
-- precisión 0.6553 y recall 0.9213; threshold_mismatches = 0.
-- -----------------------------------------------------------------------------

-- [P3c]
SELECT
  COUNT(*) AS n_rows,
  COUNTIF(pred_is_high_tip = is_high_tip_actual) / COUNT(*) AS accuracy,
  COUNTIF(pred_is_high_tip AND is_high_tip_actual) / COUNTIF(pred_is_high_tip) AS precision,
  COUNTIF(pred_is_high_tip AND is_high_tip_actual) / COUNTIF(is_high_tip_actual) AS recall,
  COUNTIF(pred_is_high_tip != (prob_high_tip >= 0.5)) AS threshold_mismatches,
  MIN(prob_high_tip) AS min_prob,
  MAX(prob_high_tip) AS max_prob,
  AVG(prob_high_tip) AS avg_prob,
  COUNTIF(is_high_tip_actual) / COUNT(*) AS actual_rate
FROM `ss2-g16-proyecto2.p2_b_ml.pred_tip_nov`;


-- -----------------------------------------------------------------------------
-- P4a: resumen diario de noviembre, tarifa real frente a predicha.
-- Pregunta: ¿cuánto se acercan las tarifas predichas por M-1 y M-2 al total
-- real de cada día?
-- - Totales diarios de fare_actual, pred_fare_m1 y pred_fare_m2, MAE diario
--   de cada modelo y diferencia porcentual del total predicho contra el real.
-- - fare_actual_ma7 y fare_pred_m2_ma7: media móvil de 7 días (el día y los
--   6 anteriores) del total diario real y del total predicho por M-2, con
--   una función de ventana. Los primeros 6 días promedian menos de 7 días.
-- - is_partial_day marca el 2022-12-01: solo trae los viajes que vienen en
--   el archivo de noviembre; sus totales no son comparables con un día
--   completo.
-- - Esta serie diaria de valores reales frente a predichos es la base de
--   datos para la comparación "(Rolling Forecast)" del tablero de B. Cómo
--   define el curso el "Rolling Forecast" sigue siendo una consulta abierta
--   al auxiliar (Q1 del steering); B decide la visualización final.
-- Resultado esperado: 31 filas (30 días de noviembre y el 2022-12-01), con
-- trips que suman 222,890. El total diario de M-2 queda cerca del real.
-- -----------------------------------------------------------------------------

-- [P4a]
WITH daily AS (
  SELECT
    pickup_date,
    COUNT(*) AS trips,
    SUM(fare_actual) AS fare_actual_total,
    SUM(pred_fare_m1) AS fare_pred_m1_total,
    SUM(pred_fare_m2) AS fare_pred_m2_total,
    AVG(abs_err_m1) AS mae_m1,
    AVG(abs_err_m2) AS mae_m2
  FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov`
  GROUP BY pickup_date
)
SELECT
  pickup_date,
  pickup_date = '2022-12-01' AS is_partial_day,
  trips,
  ROUND(fare_actual_total, 2) AS fare_actual_total,
  ROUND(fare_pred_m1_total, 2) AS fare_pred_m1_total,
  ROUND(fare_pred_m2_total, 2) AS fare_pred_m2_total,
  ROUND(100 * (fare_pred_m1_total - fare_actual_total) / fare_actual_total, 2) AS pct_diff_m1,
  ROUND(100 * (fare_pred_m2_total - fare_actual_total) / fare_actual_total, 2) AS pct_diff_m2,
  ROUND(mae_m1, 3) AS mae_m1,
  ROUND(mae_m2, 3) AS mae_m2,
  ROUND(AVG(fare_actual_total) OVER w7, 2) AS fare_actual_ma7,
  ROUND(AVG(fare_pred_m2_total) OVER w7, 2) AS fare_pred_m2_ma7
FROM daily
WINDOW w7 AS (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY pickup_date;


-- -----------------------------------------------------------------------------
-- P4b: resumen de noviembre por borough de origen.
-- Pregunta: ¿el ajuste de los modelos cambia según el borough donde empieza
-- el viaje?
-- Mismas columnas que P4a, más el RMSE de cada modelo por borough. Incluye
-- el 2022-12-01, porque aquí no se compara contra días completos.
-- Resultado esperado: trips suma 222,890; Manhattan concentra la mayoría de
-- los viajes (89.50 % de los orígenes del año, sección 6 del README).
-- -----------------------------------------------------------------------------

-- [P4b]
SELECT
  pickup_borough,
  COUNT(*) AS trips,
  ROUND(SUM(fare_actual), 2) AS fare_actual_total,
  ROUND(SUM(pred_fare_m1), 2) AS fare_pred_m1_total,
  ROUND(SUM(pred_fare_m2), 2) AS fare_pred_m2_total,
  ROUND(100 * (SUM(pred_fare_m1) - SUM(fare_actual)) / SUM(fare_actual), 2) AS pct_diff_m1,
  ROUND(100 * (SUM(pred_fare_m2) - SUM(fare_actual)) / SUM(fare_actual), 2) AS pct_diff_m2,
  ROUND(AVG(abs_err_m1), 3) AS mae_m1,
  ROUND(AVG(abs_err_m2), 3) AS mae_m2,
  ROUND(SQRT(AVG(POW(abs_err_m1, 2))), 3) AS rmse_m1,
  ROUND(SQRT(AVG(POW(abs_err_m2, 2))), 3) AS rmse_m2
FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov`
GROUP BY pickup_borough
ORDER BY trips DESC;


-- -----------------------------------------------------------------------------
-- P4c: efecto de las predicciones extremas de M-1 en los totales diarios.
-- Pregunta: ¿en qué días caen las filas de M-1 con error absoluto mayor de
-- USD 100 y cuánto mueven el total predicho de ese día?
-- - signed_err_m1 = SUM(pred_fare_m1 - fare_actual) de esas filas: positivo
--   si suben el total predicho y negativo si lo bajan.
-- - pct_diff_m1_without: diferencia porcentual del total de M-1 contra el
--   real si se quitan esas filas de los dos totales. Es un diagnóstico: las
--   tablas y la vista conservan todas las filas.
-- Resultado esperado: 14 filas en total (n_abs_err_gt_100 de M-1 en
-- noviembre, E6e de 13_evaluacion.txt).
-- -----------------------------------------------------------------------------

-- [P4c]
SELECT
  pickup_date,
  COUNTIF(abs_err_m1 > 100) AS n_abs_err_gt_100,
  ROUND(SUM(IF(abs_err_m1 > 100, pred_fare_m1 - fare_actual, 0)), 2) AS signed_err_m1,
  ROUND(MAX(abs_err_m1), 2) AS max_abs_err_m1,
  ROUND(100 * (SUM(pred_fare_m1) - SUM(fare_actual)) / SUM(fare_actual), 2) AS pct_diff_m1,
  ROUND(100 * (SUM(IF(abs_err_m1 > 100, 0, pred_fare_m1)) - SUM(IF(abs_err_m1 > 100, 0, fare_actual)))
    / SUM(IF(abs_err_m1 > 100, 0, fare_actual)), 2) AS pct_diff_m1_without
FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov`
GROUP BY pickup_date
HAVING COUNTIF(abs_err_m1 > 100) > 0
ORDER BY pickup_date;


-- -----------------------------------------------------------------------------
-- P5: vista diaria v_ml_pred_diaria para el tablero.
-- Pregunta: ¿qué objeto conecta B en Looker Studio para la serie diaria de
-- real frente a predicho?
-- - Mismo cuerpo que P4a, sin ORDER BY (el tablero ordena).
-- - Prefijo v_ml_: la vista la publica el trabajo de ML (D8). El prefijo
--   v_dash_* queda reservado para las vistas del tablero, que son de B.
-- Resultado esperado: la vista se crea y P5b devuelve 31 filas con los
-- mismos totales que P4a.
-- -----------------------------------------------------------------------------

-- [P5]
CREATE OR REPLACE VIEW `ss2-g16-proyecto2.p2_b_ml.v_ml_pred_diaria` AS
WITH daily AS (
  SELECT
    pickup_date,
    COUNT(*) AS trips,
    SUM(fare_actual) AS fare_actual_total,
    SUM(pred_fare_m1) AS fare_pred_m1_total,
    SUM(pred_fare_m2) AS fare_pred_m2_total,
    AVG(abs_err_m1) AS mae_m1,
    AVG(abs_err_m2) AS mae_m2
  FROM `ss2-g16-proyecto2.p2_b_ml.pred_fare_nov`
  GROUP BY pickup_date
)
SELECT
  pickup_date,
  pickup_date = '2022-12-01' AS is_partial_day,
  trips,
  ROUND(fare_actual_total, 2) AS fare_actual_total,
  ROUND(fare_pred_m1_total, 2) AS fare_pred_m1_total,
  ROUND(fare_pred_m2_total, 2) AS fare_pred_m2_total,
  ROUND(100 * (fare_pred_m1_total - fare_actual_total) / fare_actual_total, 2) AS pct_diff_m1,
  ROUND(100 * (fare_pred_m2_total - fare_actual_total) / fare_actual_total, 2) AS pct_diff_m2,
  ROUND(mae_m1, 3) AS mae_m1,
  ROUND(mae_m2, 3) AS mae_m2,
  ROUND(AVG(fare_actual_total) OVER w7, 2) AS fare_actual_ma7,
  ROUND(AVG(fare_pred_m2_total) OVER w7, 2) AS fare_pred_m2_ma7
FROM daily
WINDOW w7 AS (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW);


-- -----------------------------------------------------------------------------
-- P5b: control de la vista contra P4a.
-- Pregunta: ¿la vista devuelve la misma serie que la consulta de P4a?
-- Resultado esperado: 31 filas, trips = 222,890 y totales iguales a la suma
-- de las columnas de P4a.
-- -----------------------------------------------------------------------------

-- [P5b]
SELECT
  COUNT(*) AS n_days,
  COUNTIF(is_partial_day) AS n_partial_days,
  SUM(trips) AS trips,
  ROUND(SUM(fare_actual_total), 2) AS fare_actual_total,
  ROUND(SUM(fare_pred_m1_total), 2) AS fare_pred_m1_total,
  ROUND(SUM(fare_pred_m2_total), 2) AS fare_pred_m2_total
FROM `ss2-g16-proyecto2.p2_b_ml.v_ml_pred_diaria`;


-- -----------------------------------------------------------------------------
-- Conclusión (cifras de 14_predicciones.txt; detalle en su sección
-- "Conclusiones")
-- - Cobertura: pred_fare_nov tiene 222,890 filas y pred_tip_nov 172,626,
--   sin nulos (P3a). Las métricas recalculadas desde las tablas coinciden
--   con noviembre en 13_evaluacion.txt: M-1 RMSE 15.27 y R² -0.299, M-2 RMSE
--   4.24 y R² 0.900 (P3b); M-3 exactitud 0.667 (P3c).
-- - Real frente a predicho: en el mes, M-2 predice un total 3.41 % menor que
--   el real y M-1 un 2.63 % menor (P5b). En los 30 días completos M-2 va de
--   -6.34 % a +5.19 % y subestima en 27 (P4a); una tarifa promedio más alta
--   en noviembre que en ene-sep es una causa compatible (hipótesis).
-- - Predicciones extremas de M-1: 14 filas (P4c). Mueven el total de tres
--   días entre 1.2 y 4.8 puntos y dominan Staten Island (+1,016.3 %) y el
--   Bronx (+61.58 %) (P4b). En el mes su efecto neto es del 0.19 %. M-2 se
--   mantiene como modelo seleccionado y serie principal del tablero.
-- -----------------------------------------------------------------------------
