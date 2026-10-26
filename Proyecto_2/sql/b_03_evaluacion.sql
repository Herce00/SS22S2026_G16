-- =============================================================================
-- b_03_evaluacion.sql
-- Propósito : Evaluar los modelos de T3 sobre datos de retención: octubre
--             (split_set = 'eval') y noviembre (split_set = 'new'). Compara
--             cada modelo contra baselines simples, revisa la matriz de
--             confusión y la curva ROC de la logística, y pone a prueba la
--             hipótesis de sobreajuste por colinealidad de M-1 (T3).
-- Dueño     : Persona A (decisión D8 del steering; ruta B del flujo).
-- Entradas  : ss2-g16-proyecto2.p2_b_ml.features_trips (b_01_features.sql)
--             ss2-g16-proyecto2.p2_b_ml.m_fare_linreg (M-1)
--             ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd (M-2)
--             ss2-g16-proyecto2.p2_b_ml.m_tip_logreg (M-3)
--             (b_02_modelos.sql)
-- Salidas   : Solo resultados de consulta E1 a E7; no crea tablas.
-- Ejecución : Un bloque por archivo, primero con --dry_run, según
--             conventions.md:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --format=pretty < <archivo>"
-- Evidencia : Proyecto_2/evidencia/13_evaluacion.txt
-- Referencia: odd/tasks/p2-a-bqml.md (tarea T4, decisiones M1 a M4).
-- Notas     : - Cada evaluación pasa la misma lista explícita de 11 features
--               de M2 y la etiqueta del modelo. No entran trip_id,
--               pickup_month, split_set, payment_type ni la otra etiqueta
--               como input; split_set solo aparece como columna de paso en
--               ML.PREDICT para agrupar resultados.
--             - Octubre no ajustó pesos en ningún modelo. En M-3 sí definió
--               eval_loss y el corte por early_stop; por eso E5 repite la
--               evaluación sobre noviembre, que ningún modelo usó.
--             - El split 'new' incluye las filas del 2022-12-01 que vienen
--               en el archivo de noviembre (V1 de 11_features.txt).
--             - RMSE = SQRT(mean_squared_error). R² = 1 - SSE / SST, con SST
--               respecto de la media del propio conjunto evaluado.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- E1: métricas de regresión de M-1 y M-2 sobre octubre.
-- Pregunta: ¿qué tan bien predicen la tarifa los dos modelos lineales en un
-- mes que no usaron para ajustar pesos?
-- Resultado esperado: eval_rows = 250,744 (split 'eval', V1 de
-- 11_features.txt) en ambos modelos. M-2 con RMSE cercano a 4 (raíz del
-- eval_loss interno de 15.98, T3). M-1 con RMSE mucho mayor si el hallazgo
-- de T3 se repite fuera de la muestra de entrenamiento.
-- -----------------------------------------------------------------------------

-- [E1]
WITH eval_rows AS (
  SELECT COUNT(*) AS eval_rows
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'eval'
),
metrics AS (
  SELECT 'm_fare_linreg' AS model, *
  FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'eval'
  ))
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, *
  FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'eval'
  ))
)
SELECT
  m.model,
  r.eval_rows,
  m.mean_absolute_error AS mae,
  m.mean_squared_error AS mse,
  SQRT(m.mean_squared_error) AS rmse,
  m.median_absolute_error,
  m.r2_score,
  m.explained_variance
FROM metrics AS m
CROSS JOIN eval_rows AS r
ORDER BY m.model;


-- -----------------------------------------------------------------------------
-- E2: baselines de regresión sobre octubre.
-- Pregunta: ¿qué error tiene una regla trivial que no usa modelo?
-- - baseline_mean: predice siempre la tarifa promedio de 'train'.
-- - baseline_per_mile: predice la mediana de fare_amount / trip_distance en
--   'train' multiplicada por trip_distance. trip_distance >= 0.01 en la tabla
--   (V2 de 12_modelos.txt), así que la división es segura.
-- Los parámetros salen de todo 'train' (ene-sep). Un modelo solo es útil si
-- supera a estos baselines en RMSE, MAE y R².
-- Resultado esperado: eval_rows = 250,744; baseline_mean con R² cercano a 0
-- (algo negativo, porque la media de octubre es mayor: 15.24 frente a 14.46,
-- V4 de 11_features.txt); baseline_per_mile con R² positivo.
-- -----------------------------------------------------------------------------

-- [E2]
WITH train_mean AS (
  SELECT AVG(fare_amount) AS mean_fare
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
),
train_per_mile AS (
  SELECT DISTINCT
    PERCENTILE_CONT(fare_amount / trip_distance, 0.5) OVER () AS median_fare_per_mile
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
),
preds AS (
  SELECT 'baseline_mean' AS model, t.fare_amount AS actual, s.mean_fare AS predicted
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips` AS t
  CROSS JOIN train_mean AS s
  WHERE t.split_set = 'eval'
  UNION ALL
  SELECT 'baseline_per_mile' AS model, t.fare_amount AS actual,
    p.median_fare_per_mile * t.trip_distance AS predicted
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips` AS t
  CROSS JOIN train_per_mile AS p
  WHERE t.split_set = 'eval'
)
SELECT
  model,
  COUNT(*) AS eval_rows,
  ANY_VALUE(param) AS param,
  SQRT(AVG(POW(actual - predicted, 2))) AS rmse,
  AVG(ABS(actual - predicted)) AS mae,
  1 - SUM(POW(actual - predicted, 2)) / SUM(POW(actual - avg_actual, 2)) AS r2
FROM (
  SELECT
    p.*,
    AVG(p.actual) OVER (PARTITION BY p.model) AS avg_actual,
    CASE p.model
      WHEN 'baseline_mean' THEN (SELECT mean_fare FROM train_mean)
      ELSE (SELECT median_fare_per_mile FROM train_per_mile)
    END AS param
  FROM preds AS p
)
GROUP BY model
ORDER BY model;


-- -----------------------------------------------------------------------------
-- E3: métricas de clasificación de M-3 sobre octubre y baseline de clase
-- mayoritaria.
-- Pregunta: ¿cuánto mejora la logística a una regla que siempre predice la
-- clase mayoritaria de 'train'?
-- - Umbral por defecto (0.5) de ML.EVALUATE.
-- - baseline: la clase mayoritaria de 'train' con tarjeta (TRUE, 60.28 %, V6
--   de 11_features.txt). Su exactitud en octubre es la proporción de esa
--   clase en octubre. Su log_loss usa como probabilidad constante la
--   proporción de TRUE en 'train'. Un puntaje constante tiene ROC-AUC 0.5.
-- Resultado esperado: card_rows = 194,093 (filas con tarjeta de 'eval', V6
-- de 11_features.txt); baseline_accuracy cercana a 0.5873; el modelo con
-- exactitud mayor que el baseline y ROC-AUC mayor que 0.5.
-- -----------------------------------------------------------------------------

-- [E3]
WITH train_prior AS (
  SELECT COUNTIF(is_high_tip) / COUNT(*) AS p_true
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
    AND is_high_tip IS NOT NULL
),
baseline AS (
  SELECT
    COUNT(*) AS card_rows,
    COUNTIF(is_high_tip = (p.p_true >= 0.5)) / COUNT(*) AS baseline_accuracy,
    -AVG(IF(is_high_tip, LN(p.p_true), LN(1 - p.p_true))) AS baseline_log_loss,
    ANY_VALUE(p.p_true) AS train_p_true
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  CROSS JOIN train_prior AS p
  WHERE split_set = 'eval'
    AND is_high_tip IS NOT NULL
)
SELECT
  b.card_rows,
  m.precision,
  m.recall,
  m.accuracy,
  m.f1_score,
  m.log_loss,
  m.roc_auc,
  b.train_p_true,
  b.baseline_accuracy,
  b.baseline_log_loss,
  m.accuracy - b.baseline_accuracy AS accuracy_lift
FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
  SELECT
    pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
    pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
    vendor_id, rate_code_imp, is_high_tip
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'eval'
    AND is_high_tip IS NOT NULL
)) AS m
CROSS JOIN baseline AS b;


-- -----------------------------------------------------------------------------
-- E4a: matriz de confusión de M-3 sobre octubre con umbral 0.5.
-- Pregunta: ¿cómo se reparten los aciertos y errores entre las dos clases?
-- Resultado esperado: la suma de las cuatro celdas es 194,093. La fila
-- expected_label = TRUE suma las propinas altas de octubre (113,988, V6 de
-- 11_features.txt).
-- -----------------------------------------------------------------------------

-- [E4a]
SELECT *
FROM ML.CONFUSION_MATRIX(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
  SELECT
    pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
    pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
    vendor_id, rate_code_imp, is_high_tip
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'eval'
    AND is_high_tip IS NOT NULL
), STRUCT(0.5 AS threshold));


-- -----------------------------------------------------------------------------
-- E4b: curva ROC de M-3 sobre octubre en 9 umbrales de 0.1 a 0.9.
-- Pregunta: ¿cómo cambian recall y tasa de falsos positivos al mover el
-- umbral? El ROC-AUC sale de E3.
-- Resultado esperado: recall y false_positive_rate bajan al subir el umbral;
-- en cada fila TP + FN = 113,988 y FP + TN = 80,105 (V6 de
-- 11_features.txt).
-- Los umbrales van como arreglo literal para que tengan valores exactos
-- (GENERATE_ARRAY(0.1, 0.9, 0.1) termina en 0.8999999999999999).
-- -----------------------------------------------------------------------------

-- [E4b]
SELECT
  ROUND(threshold, 2) AS threshold,
  recall,
  false_positive_rate,
  true_positives,
  false_positives,
  true_negatives,
  false_negatives
FROM ML.ROC_CURVE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
  SELECT
    pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
    pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
    vendor_id, rate_code_imp, is_high_tip
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'eval'
    AND is_high_tip IS NOT NULL
), [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
ORDER BY threshold;


-- -----------------------------------------------------------------------------
-- E4c: distribución de la probabilidad predicha de M-3 en octubre.
-- Pregunta: ¿en qué rango caen las probabilidades de propina alta que
-- produce el modelo?
-- Explica la forma de E4b: si casi ninguna probabilidad supera un umbral,
-- recall y false_positive_rate caen a cerca de 0 en ese umbral. Los
-- percentiles salen de APPROX_QUANTILES(x, 100) y son aproximados.
-- Resultado esperado: probabilidades concentradas alrededor de la proporción
-- de TRUE de 'train' (0.60), con pocas filas por encima de 0.8.
-- -----------------------------------------------------------------------------

-- [E4c]
WITH probs AS (
  SELECT (
    SELECT p.prob FROM UNNEST(predicted_is_high_tip_probs) AS p WHERE p.label
  ) AS prob_true
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, is_high_tip
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'eval'
      AND is_high_tip IS NOT NULL
  ))
)
SELECT
  COUNT(*) AS n_rows,
  MIN(prob_true) AS min_prob,
  APPROX_QUANTILES(prob_true, 100)[OFFSET(10)] AS p10_prob,
  APPROX_QUANTILES(prob_true, 100)[OFFSET(50)] AS p50_prob,
  APPROX_QUANTILES(prob_true, 100)[OFFSET(90)] AS p90_prob,
  APPROX_QUANTILES(prob_true, 100)[OFFSET(99)] AS p99_prob,
  MAX(prob_true) AS max_prob,
  COUNTIF(prob_true >= 0.8) AS n_prob_ge_0_8,
  COUNTIF(prob_true >= 0.9) AS n_prob_ge_0_9
FROM probs;


-- -----------------------------------------------------------------------------
-- E5a: métricas de regresión de M-1 y M-2 sobre noviembre.
-- Pregunta: ¿las métricas de octubre se mantienen en un mes que ningún
-- modelo usó de ninguna forma?
-- Resultado esperado: new_rows = 222,890 (split 'new', V1 de
-- 11_features.txt); métricas de M-2 parecidas a las de octubre (E1).
-- -----------------------------------------------------------------------------

-- [E5a]
WITH new_rows AS (
  SELECT COUNT(*) AS new_rows
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'new'
),
metrics AS (
  SELECT 'm_fare_linreg' AS model, *
  FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'new'
  ))
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, *
  FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'new'
  ))
)
SELECT
  m.model,
  r.new_rows,
  m.mean_absolute_error AS mae,
  m.mean_squared_error AS mse,
  SQRT(m.mean_squared_error) AS rmse,
  m.median_absolute_error,
  m.r2_score,
  m.explained_variance
FROM metrics AS m
CROSS JOIN new_rows AS r
ORDER BY m.model;


-- -----------------------------------------------------------------------------
-- E5b: métricas de clasificación de M-3 en octubre frente a noviembre.
-- Pregunta: como octubre definió el corte por early_stop de M-3, ¿el
-- resultado se sostiene en noviembre, que el modelo nunca vio?
-- Resultado esperado: card_rows = 194,093 en octubre y 172,626 en
-- noviembre (V6 de 11_features.txt); ROC-AUC y exactitud de noviembre
-- cercanos a los de octubre. Si noviembre es claramente peor, el corte por
-- early_stop habría favorecido a octubre.
-- -----------------------------------------------------------------------------

-- [E5b]
SELECT 'eval' AS split_set, *
FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
  SELECT
    pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
    pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
    vendor_id, rate_code_imp, is_high_tip
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'eval'
    AND is_high_tip IS NOT NULL
))
UNION ALL
SELECT 'new' AS split_set, *
FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
  SELECT
    pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
    pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
    vendor_id, rate_code_imp, is_high_tip
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'new'
    AND is_high_tip IS NOT NULL
))
ORDER BY split_set;


-- -----------------------------------------------------------------------------
-- E6a: magnitud de los pesos de M-1 y M-2.
-- Pregunta: ¿los pesos de M-1 son mucho más grandes que los de M-2, como
-- predice la hipótesis de colinealidad de T3?
-- ML.WEIGHTS da un peso por feature numérica y un peso por categoría en las
-- features categóricas (category_weights); aquí se aplanan ambos. La fila
-- __INTERCEPT__ es el intercepto.
-- Resultado esperado: si la hipótesis es cierta, M-1 tiene pesos absolutos
-- muy por encima de la tarifa promedio (14.46) y M-2 no.
-- -----------------------------------------------------------------------------

-- [E6a]
WITH weights AS (
  SELECT 'm_fare_linreg' AS model, processed_input, CAST(NULL AS STRING) AS category, weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`)
  WHERE ARRAY_LENGTH(category_weights) = 0
  UNION ALL
  SELECT 'm_fare_linreg' AS model, processed_input, cw.category, cw.weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`), UNNEST(category_weights) AS cw
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, processed_input, CAST(NULL AS STRING) AS category, weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`)
  WHERE ARRAY_LENGTH(category_weights) = 0
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, processed_input, cw.category, cw.weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`), UNNEST(category_weights) AS cw
)
SELECT
  model,
  COUNT(*) AS n_weights,
  MAX(ABS(weight)) AS max_abs_weight,
  APPROX_QUANTILES(ABS(weight), 100)[OFFSET(50)] AS p50_abs_weight,
  COUNTIF(ABS(weight) > 100) AS n_abs_gt_100,
  COUNTIF(ABS(weight) > 1000) AS n_abs_gt_1000,
  ANY_VALUE(IF(processed_input = '__INTERCEPT__', weight, NULL)) AS intercept,
  ANY_VALUE(IF(processed_input = 'trip_distance', weight, NULL)) AS w_trip_distance
FROM weights
GROUP BY model
ORDER BY model;


-- -----------------------------------------------------------------------------
-- E6b: los 10 pesos de M-1 con mayor valor absoluto, junto al peso de M-2
-- para la misma feature y categoría.
-- Pregunta: ¿qué features concentran los pesos extremos de M-1?
-- Resultado esperado: si la hipótesis es cierta, aparecen categorías de
-- zonas, boroughs o el par passenger_missing / rate_code_imp, con signos que
-- se compensan, y M-2 tiene pesos pequeños para las mismas categorías.
-- -----------------------------------------------------------------------------

-- [E6b]
WITH weights AS (
  SELECT 'm_fare_linreg' AS model, processed_input, CAST(NULL AS STRING) AS category, weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`)
  WHERE ARRAY_LENGTH(category_weights) = 0
  UNION ALL
  SELECT 'm_fare_linreg' AS model, processed_input, cw.category, cw.weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`), UNNEST(category_weights) AS cw
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, processed_input, CAST(NULL AS STRING) AS category, weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`)
  WHERE ARRAY_LENGTH(category_weights) = 0
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, processed_input, cw.category, cw.weight
  FROM ML.WEIGHTS(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`), UNNEST(category_weights) AS cw
)
SELECT
  m1.processed_input,
  m1.category,
  m1.weight AS weight_m1,
  m2.weight AS weight_m2
FROM weights AS m1
LEFT JOIN weights AS m2
  ON m2.model = 'm_fare_linreg_gd'
  AND m2.processed_input = m1.processed_input
  AND IFNULL(m2.category, '') = IFNULL(m1.category, '')
WHERE m1.model = 'm_fare_linreg'
ORDER BY ABS(m1.weight) DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- E6c: colinealidad exacta en los datos de entrenamiento.
-- Pregunta: ¿las features que señala la hipótesis son colineales de forma
-- exacta en 'train'?
-- - Cada zona debería tener un solo borough (zonas deduplicadas, M7).
-- - passenger_missing = TRUE debería coincidir con rate_code_imp = 'NA' (M6).
-- Resultado esperado: 0 zonas con más de un borough en origen y destino, y
-- 0 filas donde passenger_missing y rate_code_imp = 'NA' difieren. Si se
-- cumple, la colinealidad exacta queda probada en los datos; que sea la causa
-- del error de M-1 sigue siendo una inferencia.
-- -----------------------------------------------------------------------------

-- [E6c]
WITH train AS (
  SELECT pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
    passenger_missing, rate_code_imp
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
)
SELECT
  (SELECT COUNT(*) FROM (
    SELECT pickup_location_id FROM train
    GROUP BY pickup_location_id HAVING COUNT(DISTINCT pickup_borough) > 1
  )) AS pickup_zones_multi_borough,
  (SELECT COUNT(*) FROM (
    SELECT dropoff_location_id FROM train
    GROUP BY dropoff_location_id HAVING COUNT(DISTINCT dropoff_borough) > 1
  )) AS dropoff_zones_multi_borough,
  (SELECT COUNTIF(passenger_missing) FROM train) AS passenger_missing_rows,
  (SELECT COUNTIF(rate_code_imp = 'NA') FROM train) AS rate_code_na_rows,
  (SELECT COUNTIF(passenger_missing != (rate_code_imp = 'NA')) FROM train) AS mismatched_rows;


-- -----------------------------------------------------------------------------
-- E6d: los 10 errores absolutos más grandes de M-1 en noviembre.
-- Pregunta: ¿el error de M-1 se reparte entre muchas filas o se concentra en
-- pocas, y esas filas tienen zonas raras o ausentes en 'train'?
-- - trip_id solo es columna de paso para unir las predicciones de M-1 y M-2;
--   ML.PREDICT usa únicamente las features con las que se entrenó el modelo.
-- - train_rows_pickup_zone y train_rows_dropoff_zone cuentan las filas de
--   'train' con esa zona. M-1 ajustó con un 80 % aleatorio de 'train', así
--   que una zona con muy pocas filas pudo quedar fuera de su ajuste.
-- Resultado esperado: si los pesos de E6a se cancelan entre zona y borough,
-- una zona sin peso propio deja sin compensar el peso de su borough y la
-- predicción se dispara; se esperan zonas con 0 o muy pocas filas en
-- 'train' y una predicción de M-2 cercana a la tarifa real.
-- -----------------------------------------------------------------------------

-- [E6d]
WITH train_zones AS (
  SELECT 'pickup' AS side, pickup_location_id AS zone_id, COUNT(*) AS train_rows
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
  GROUP BY pickup_location_id
  UNION ALL
  SELECT 'dropoff' AS side, dropoff_location_id AS zone_id, COUNT(*) AS train_rows
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
  GROUP BY dropoff_location_id
),
m1 AS (
  SELECT trip_id, pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
    trip_distance, fare_amount, predicted_fare_amount AS pred_m1
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
  SELECT trip_id, predicted_fare_amount AS pred_m2
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`, (
    SELECT
      trip_id, pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'new'
  ))
)
SELECT
  m1.pickup_location_id AS pu_zone,
  m1.pickup_borough AS pu_borough,
  IFNULL(pz.train_rows, 0) AS train_rows_pickup_zone,
  m1.dropoff_location_id AS do_zone,
  m1.dropoff_borough AS do_borough,
  IFNULL(dz.train_rows, 0) AS train_rows_dropoff_zone,
  m1.trip_distance,
  m1.fare_amount,
  ROUND(m1.pred_m1, 2) AS pred_m1,
  ROUND(m2.pred_m2, 2) AS pred_m2
FROM m1
JOIN m2
  ON m2.trip_id = m1.trip_id
LEFT JOIN train_zones AS pz
  ON pz.side = 'pickup' AND pz.zone_id = m1.pickup_location_id
LEFT JOIN train_zones AS dz
  ON dz.side = 'dropoff' AND dz.zone_id = m1.dropoff_location_id
ORDER BY ABS(m1.fare_amount - m1.pred_m1) DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- E6e: concentración del error cuadrático de M-1 y M-2 por mes.
-- Pregunta: ¿qué parte del SSE se debe a filas con error absoluto mayor de
-- USD 100 y cómo quedaría el RMSE sin ellas?
-- Es un diagnóstico, no una métrica de entrega: quitar filas del conjunto
-- de evaluación no es válido para comparar modelos, y la tabla de E7a se
-- mantiene completa.
-- Resultado esperado: si la falla de M-1 está en pocas filas, n_abs_err_gt_100
-- es pequeño, share_sse_gt_100 es alto y rmse_without_gt_100 queda cerca del
-- de M-2.
-- -----------------------------------------------------------------------------

-- [E6e]
WITH preds AS (
  SELECT 'm_fare_linreg' AS model, split_set, fare_amount - predicted_fare_amount AS err
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount, split_set
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set IN ('eval', 'new')
  ))
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, split_set, fare_amount - predicted_fare_amount AS err
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount, split_set
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set IN ('eval', 'new')
  ))
)
SELECT
  split_set,
  model,
  COUNT(*) AS n_rows,
  COUNTIF(ABS(err) > 100) AS n_abs_err_gt_100,
  MAX(ABS(err)) AS max_abs_err,
  SUM(IF(ABS(err) > 100, POW(err, 2), 0)) / SUM(POW(err, 2)) AS share_sse_gt_100,
  SQRT(AVG(IF(ABS(err) <= 100, POW(err, 2), NULL))) AS rmse_without_gt_100
FROM preds
GROUP BY split_set, model
ORDER BY split_set, model;


-- -----------------------------------------------------------------------------
-- E7a: tabla comparativa de regresión, modelos y baselines, en octubre y
-- noviembre.
-- Pregunta: ¿qué modelo de tarifa rinde mejor en cada mes y cuánto supera a
-- los baselines?
-- Todas las filas usan las mismas fórmulas sobre ML.PREDICT o sobre la
-- predicción del baseline (parámetros de E2, calculados en 'train'), así
-- que la comparación es homogénea. Las métricas de los modelos deben
-- coincidir con E1 (octubre) y E5a (noviembre).
-- Resultado esperado: 250,744 filas por fila de octubre y 222,890 por fila
-- de noviembre; M-2 con menor RMSE que ambos baselines en los dos meses.
-- -----------------------------------------------------------------------------

-- [E7a]
WITH train_mean AS (
  SELECT AVG(fare_amount) AS mean_fare
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
),
train_per_mile AS (
  SELECT DISTINCT
    PERCENTILE_CONT(fare_amount / trip_distance, 0.5) OVER () AS median_fare_per_mile
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
),
preds AS (
  SELECT 'm_fare_linreg' AS model, split_set, fare_amount AS actual,
    predicted_fare_amount AS predicted
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount, split_set
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set IN ('eval', 'new')
  ))
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, split_set, fare_amount AS actual,
    predicted_fare_amount AS predicted
  FROM ML.PREDICT(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, fare_amount, split_set
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set IN ('eval', 'new')
  ))
  UNION ALL
  SELECT 'baseline_mean' AS model, t.split_set, t.fare_amount AS actual,
    s.mean_fare AS predicted
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips` AS t
  CROSS JOIN train_mean AS s
  WHERE t.split_set IN ('eval', 'new')
  UNION ALL
  SELECT 'baseline_per_mile' AS model, t.split_set, t.fare_amount AS actual,
    p.median_fare_per_mile * t.trip_distance AS predicted
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips` AS t
  CROSS JOIN train_per_mile AS p
  WHERE t.split_set IN ('eval', 'new')
)
SELECT
  split_set,
  model,
  COUNT(*) AS n_rows,
  SQRT(AVG(POW(actual - predicted, 2))) AS rmse,
  AVG(ABS(actual - predicted)) AS mae,
  1 - SUM(POW(actual - predicted, 2)) / SUM(POW(actual - avg_actual, 2)) AS r2
FROM (
  SELECT *, AVG(actual) OVER (PARTITION BY model, split_set) AS avg_actual
  FROM preds
)
GROUP BY split_set, model
ORDER BY split_set, rmse;


-- -----------------------------------------------------------------------------
-- E7b: tabla comparativa de clasificación, M-3 y baseline de clase
-- mayoritaria, en octubre y noviembre.
-- Pregunta: ¿cuánto supera M-3 al baseline en cada mes?
-- - Filas del modelo: ML.EVALUATE con umbral 0.5 (las mismas cifras de E3 y
--   E5b).
-- - Filas del baseline: predice siempre la clase mayoritaria de 'train'
--   (TRUE). Con esa regla, precision = proporción de TRUE del mes, recall =
--   1 y F1 = 2 · precision / (1 + precision). log_loss usa la proporción de
--   TRUE de 'train' como probabilidad constante y el ROC-AUC de un puntaje
--   constante es 0.5.
-- Resultado esperado: 194,093 filas en octubre y 172,626 en noviembre; M-3
-- con exactitud y ROC-AUC mayores que el baseline en los dos meses.
-- -----------------------------------------------------------------------------

-- [E7b]
WITH train_prior AS (
  SELECT COUNTIF(is_high_tip) / COUNT(*) AS p_true
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set = 'train'
    AND is_high_tip IS NOT NULL
),
card AS (
  SELECT split_set, is_high_tip
  FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
  WHERE split_set IN ('eval', 'new')
    AND is_high_tip IS NOT NULL
),
baseline AS (
  SELECT
    c.split_set,
    'baseline_majority' AS model,
    COUNT(*) AS n_rows,
    COUNTIF(c.is_high_tip = (p.p_true >= 0.5)) / COUNT(*) AS accuracy,
    COUNTIF(c.is_high_tip) / COUNT(*) AS precision,
    1.0 AS recall,
    2 * (COUNTIF(c.is_high_tip) / COUNT(*)) / (1 + COUNTIF(c.is_high_tip) / COUNT(*)) AS f1_score,
    -AVG(IF(c.is_high_tip, LN(p.p_true), LN(1 - p.p_true))) AS log_loss,
    0.5 AS roc_auc
  FROM card AS c
  CROSS JOIN train_prior AS p
  GROUP BY c.split_set
),
row_counts AS (
  SELECT split_set, COUNT(*) AS n_rows
  FROM card
  GROUP BY split_set
),
model_metrics AS (
  SELECT 'eval' AS split_set, *
  FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, is_high_tip
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'eval'
      AND is_high_tip IS NOT NULL
  ))
  UNION ALL
  SELECT 'new' AS split_set, *
  FROM ML.EVALUATE(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`, (
    SELECT
      pickup_hour, pickup_dow, trip_distance, passenger_count_imp, passenger_missing,
      pickup_location_id, dropoff_location_id, pickup_borough, dropoff_borough,
      vendor_id, rate_code_imp, is_high_tip
    FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
    WHERE split_set = 'new'
      AND is_high_tip IS NOT NULL
  ))
)
SELECT split_set, model, n_rows, accuracy, precision, recall, f1_score, log_loss, roc_auc
FROM baseline
UNION ALL
SELECT m.split_set, 'm_tip_logreg' AS model, r.n_rows, m.accuracy, m.precision, m.recall,
  m.f1_score, m.log_loss, m.roc_auc
FROM model_metrics AS m
JOIN row_counts AS r
  ON r.split_set = m.split_set
ORDER BY split_set, model;


-- -----------------------------------------------------------------------------
-- Conclusión (cifras de 13_evaluacion.txt; detalle en su sección
-- "Conclusiones")
-- - Regresión: el modelo recomendado es M-2 (m_fare_linreg_gd). En octubre
--   M-1 rinde algo mejor (RMSE 3.93 frente a 4.32, R² 0.915 frente a 0.898),
--   pero en noviembre colapsa (RMSE 15.27, R² -0.30) mientras M-2 se
--   mantiene (RMSE 4.24, R² 0.900). Los dos superan con amplitud a los
--   baselines (el mejor, tarifa por milla: RMSE 12.52 en octubre y 12.30 en
--   noviembre).
-- - Por qué: los datos tienen colinealidad exacta (E6c: cada zona tiene un
--   solo borough y passenger_missing coincide con rate_code_imp = 'NA') y
--   M-1, sin regularización, tiene pesos de miles que se compensan (E6a:
--   máximo absoluto 20,163 frente a 35.97 en M-2). El 94 % del SSE de M-1 en
--   noviembre sale de 14 filas (E6e); las tres peores tienen zonas de origen
--   con 0 o 1 fila en 'train' (E6d). Que una zona sin peso propio deje sin
--   compensar el peso de su borough es el mecanismo probable (hipótesis).
--   L2 en M-2 mantiene los pesos acotados y la predicción estable.
-- - Clasificación: M-3 supera al baseline de clase mayoritaria en exactitud
--   por 7.85 puntos en octubre (0.6658 frente a 0.5873) y 7.72 en noviembre
--   (0.6675 frente a 0.5903), con ROC-AUC de 0.692 frente a 0.5 y log_loss
--   de 0.621 frente a 0.678. Noviembre repite las cifras de octubre, así que
--   el corte por early_stop no favoreció a octubre. La separación es
--   moderada: las probabilidades no pasan de 0.83 (E4c); la decisión de
--   propina depende de factores que no se conocen al inicio del viaje
--   (hipótesis).
-- -----------------------------------------------------------------------------
