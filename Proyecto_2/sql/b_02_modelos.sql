-- =============================================================================
-- b_02_modelos.sql
-- Propósito : Entrenar los modelos de BigQuery ML sobre la tabla de features
--             de T2: una regresión lineal para fare_amount con el optimizador
--             por defecto (M-1), una variante de hiperparámetros de la misma
--             regresión (M-2) y una regresión logística para is_high_tip
--             (M-3). Incluye las validaciones de entrenamiento: iteraciones y
--             pérdida, lista de features (control de leakage), explicaciones
--             globales y bytes de cada CREATE MODEL.
-- Dueño     : Persona A (decisión D8 del steering; ruta B del flujo).
-- Entradas  : ss2-g16-proyecto2.p2_b_ml.features_trips (b_01_features.sql;
--             2,482,519 filas: train 2,008,885, eval 250,744, new 222,890).
-- Salidas   : ss2-g16-proyecto2.p2_b_ml.m_fare_linreg
--             ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd
--             ss2-g16-proyecto2.p2_b_ml.m_tip_logreg
--             Resultados de consulta V1 a V6.
-- Ejecución : Un bloque por archivo, primero con --dry_run, según
--             conventions.md. Cada CREATE MODEL lleva un --job_id
--             determinístico (p2_bqml_m1_<unixts>, p2_bqml_m2_<unixts>,
--             p2_bqml_m3_<unixts>) para ubicarlo en V6:
--             cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2
--               query --use_legacy_sql=false --format=pretty
--               [--job_id=...] < <archivo>"
-- Evidencia : Proyecto_2/evidencia/12_modelos.txt
-- Referencia: odd/tasks/p2-a-bqml.md (tarea T3, decisiones M1 a M5).
-- Notas     : - Cada modelo selecciona solo la lista explícita de 11 features
--               (M2), su etiqueta y, en M-3, la columna de split. Nunca entran
--               trip_id, pickup_month, split_set, payment_type ni la etiqueta
--               del otro modelo.
--             - Las 11 features: pickup_hour, pickup_dow, trip_distance,
--               passenger_count_imp, passenger_missing, pickup_location_id,
--               dropoff_location_id, pickup_borough, dropoff_borough,
--               vendor_id y rate_code_imp.
--             - Octubre (split_set = 'eval') queda reservado para la
--               evaluación de T4. M-1 y M-2 no lo leen. M-3 lo usa como
--               conjunto de evaluación del split CUSTOM: no ajusta pesos con
--               esas filas, pero sí calcula eval_loss sobre ellas.
--             - Costo: la creación de modelos se factura con una tarifa por
--               TB más alta que las consultas. La cifra que suele citarse
--               (unos USD 250 por TB para regresión lineal y logística) es de
--               terceros y no está verificada en la página oficial; por eso
--               V6 reporta solo bytes facturados.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- M1: regresión lineal de fare_amount con el optimizador por defecto.
-- Pregunta: ¿qué tan bien explican las features conocidas al inicio del viaje
-- la tarifa base, sin ajustar hiperparámetros?
-- - Modelo de referencia de la familia de regresión (M1): se evalúa con RMSE,
--   MAE y R² en T4.
-- - Split RANDOM con data_split_eval_fraction = 0.2 (M4): BigQuery ML separa
--   al azar el 20 % de las filas de ene-sep para la evaluación interna. Es el
--   primer mecanismo de split que pide el enunciado. Octubre no entra: queda
--   como prueba de retención que el modelo nunca ve.
-- - Optimizador por defecto (AUTO_STRATEGY): BigQuery elige entre la ecuación
--   normal y el descenso de gradiente según el tamaño del problema. La
--   estrategia elegida se documenta con ML.TRAINING_INFO (V1) y con bq show.
-- - enable_global_explain = TRUE permite ML.GLOBAL_EXPLAIN (V4).
-- -----------------------------------------------------------------------------

-- [M1]
CREATE OR REPLACE MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`
OPTIONS (
  model_type = 'LINEAR_REG',
  input_label_cols = ['fare_amount'],
  data_split_method = 'RANDOM',
  data_split_eval_fraction = 0.2,
  enable_global_explain = TRUE
) AS
SELECT
  pickup_hour,
  pickup_dow,
  trip_distance,
  passenger_count_imp,
  passenger_missing,
  pickup_location_id,
  dropoff_location_id,
  pickup_borough,
  dropoff_borough,
  vendor_id,
  rate_code_imp,
  fare_amount
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
WHERE split_set = 'train';


-- -----------------------------------------------------------------------------
-- M2: variante de hiperparámetros de la regresión lineal.
-- Pregunta: ¿cambia el ajuste al forzar descenso de gradiente con
-- regularización L2 sobre los mismos datos y la misma etiqueta?
-- - Mismos datos, misma etiqueta y mismo split RANDOM con fracción 0.2 que M1:
--   la única diferencia son los hiperparámetros, así que la comparación de T4
--   aísla su efecto.
-- - optimize_strategy = 'BATCH_GRADIENT_DESCENT': expone la curva de
--   iteraciones y pérdida (loss y eval_loss por iteración) que pide el
--   enunciado. La ecuación normal resuelve en un solo paso y no muestra esa
--   curva.
-- - max_iterations = 20 con early_stop = TRUE: como máximo 20 pasadas; se
--   detiene antes si la mejora relativa de la pérdida cae por debajo de
--   min_rel_progress (valor por defecto).
-- - learn_rate_strategy = 'LINE_SEARCH': la tasa de aprendizaje se ajusta en
--   cada iteración, sin fijar un valor a mano.
-- - l2_reg = 1.0: agrega regularización L2, que penaliza pesos grandes en las
--   515 categorías one-hot de zonas (254 de origen y 261 de destino, V5 de
--   11_features.txt) y reduce el sobreajuste a zonas con pocos viajes.
-- -----------------------------------------------------------------------------

-- [M2]
CREATE OR REPLACE MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`
OPTIONS (
  model_type = 'LINEAR_REG',
  input_label_cols = ['fare_amount'],
  data_split_method = 'RANDOM',
  data_split_eval_fraction = 0.2,
  optimize_strategy = 'BATCH_GRADIENT_DESCENT',
  max_iterations = 20,
  l2_reg = 1.0,
  learn_rate_strategy = 'LINE_SEARCH',
  early_stop = TRUE
) AS
SELECT
  pickup_hour,
  pickup_dow,
  trip_distance,
  passenger_count_imp,
  passenger_missing,
  pickup_location_id,
  dropoff_location_id,
  pickup_borough,
  dropoff_borough,
  vendor_id,
  rate_code_imp,
  fare_amount
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
WHERE split_set = 'train';


-- -----------------------------------------------------------------------------
-- M3: regresión logística de is_high_tip con split CUSTOM temporal.
-- Pregunta: ¿se puede anticipar, al inicio de un viaje pagado con tarjeta, si
-- la propina será de al menos el 25 % de la tarifa?
-- - Familia de clasificación (M1): se evalúa con ROC-AUC, precisión, recall y
--   matriz de confusión en T4. La etiqueta is_high_tip tiene clases parejas
--   (60.01 % TRUE, V6 de 11_features.txt), a diferencia de is_tipped (96.40 %).
-- - Solo pagos con tarjeta (M3): is_high_tip IS NOT NULL equivale a
--   payment_type = '1'. payment_type no entra como feature; con todos los
--   pagos, el modelo aprendería "efectivo = sin propina".
-- - Split CUSTOM (M4): data_split_col = 'is_eval'. Las filas con FALSE
--   (ene-sep) entrenan y las filas con TRUE (octubre) evalúan. Es el segundo
--   mecanismo de split que pide el enunciado y es temporal: el modelo no
--   aprende del futuro. BigQuery ML excluye la columna de split de las
--   features; V2 y V3 lo comprueban.
-- - max_iterations = 20 y l2_reg = 0.1: regularización más suave que M2,
--   porque la logística ya acota sus salidas y la etiqueta tiene ruido propio
--   de la decisión de cada pasajero.
-- - enable_global_explain = TRUE permite ML.GLOBAL_EXPLAIN (V5).
-- -----------------------------------------------------------------------------

-- [M3]
CREATE OR REPLACE MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`
OPTIONS (
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['is_high_tip'],
  data_split_method = 'CUSTOM',
  data_split_col = 'is_eval',
  max_iterations = 20,
  l2_reg = 0.1,
  enable_global_explain = TRUE
) AS
SELECT
  pickup_hour,
  pickup_dow,
  trip_distance,
  passenger_count_imp,
  passenger_missing,
  pickup_location_id,
  dropoff_location_id,
  pickup_borough,
  dropoff_borough,
  vendor_id,
  rate_code_imp,
  is_eval,
  is_high_tip
FROM `ss2-g16-proyecto2.p2_b_ml.features_trips`
WHERE split_set IN ('train', 'eval')
  AND is_high_tip IS NOT NULL;


-- -----------------------------------------------------------------------------
-- V1: iteraciones y pérdida de los tres modelos.
-- Pregunta: ¿cuántas iteraciones hizo cada modelo y cómo evolucionaron la
-- pérdida de entrenamiento y la de evaluación?
-- Resultado esperado: M-1 con su optimizador por defecto (probablemente 1
-- iteración si BigQuery eligió la ecuación normal); M-2 y M-3 con varias
-- iteraciones y una pérdida que baja hasta el corte por early_stop o por
-- max_iterations.
-- -----------------------------------------------------------------------------

-- [V1]
SELECT 'm_fare_linreg' AS model, iteration, loss, eval_loss, learning_rate, duration_ms
FROM ML.TRAINING_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`)
UNION ALL
SELECT 'm_fare_linreg_gd' AS model, iteration, loss, eval_loss, learning_rate, duration_ms
FROM ML.TRAINING_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`)
UNION ALL
SELECT 'm_tip_logreg' AS model, iteration, loss, eval_loss, learning_rate, duration_ms
FROM ML.TRAINING_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`)
ORDER BY model, iteration;


-- -----------------------------------------------------------------------------
-- V2: features de entrada de M-1 y M-3.
-- Pregunta: ¿qué columnas recibió cada modelo como input y con qué
-- estadísticas?
-- Resultado esperado: las mismas 11 features en ambos modelos, sin is_eval en
-- M-3. category_count de las zonas igual o menor que en la tabla completa
-- (254 de origen y 261 de destino) y null_count = 0 en todas (V2 y V5 de
-- 11_features.txt).
-- -----------------------------------------------------------------------------

-- [V2]
SELECT 'm_fare_linreg' AS model, input, min, max, mean, stddev, category_count, null_count
FROM ML.FEATURE_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`)
UNION ALL
SELECT 'm_tip_logreg' AS model, input, min, max, mean, stddev, category_count, null_count
FROM ML.FEATURE_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`)
ORDER BY model, input;


-- -----------------------------------------------------------------------------
-- V3: control de leakage sobre las features de entrada.
-- Pregunta: ¿algún modelo recibió una columna excluida (identificador, mes,
-- columnas de split, payment_type o etiquetas)?
-- Compara ML.FEATURE_INFO de los tres modelos contra la lista intencional de
-- M2 y contra la lista de columnas excluidas.
-- Resultado esperado: n_features = 11, matched_intended = 11 y
-- excluded_present = 0 en los tres modelos.
-- -----------------------------------------------------------------------------

-- [V3]
WITH inputs AS (
  SELECT 'm_fare_linreg' AS model, input
  FROM ML.FEATURE_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`)
  UNION ALL
  SELECT 'm_fare_linreg_gd' AS model, input
  FROM ML.FEATURE_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg_gd`)
  UNION ALL
  SELECT 'm_tip_logreg' AS model, input
  FROM ML.FEATURE_INFO(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`)
)
SELECT
  model,
  COUNT(*) AS n_features,
  COUNTIF(input IN ('pickup_hour', 'pickup_dow', 'trip_distance', 'passenger_count_imp',
    'passenger_missing', 'pickup_location_id', 'dropoff_location_id', 'pickup_borough',
    'dropoff_borough', 'vendor_id', 'rate_code_imp')) AS matched_intended,
  COUNTIF(input IN ('trip_id', 'pickup_month', 'split_set', 'is_eval', 'payment_type',
    'fare_amount', 'is_tipped', 'is_high_tip')) AS excluded_present
FROM inputs
GROUP BY model
ORDER BY model;


-- -----------------------------------------------------------------------------
-- V4: explicación global de M-1 (10 features con mayor atribución).
-- Pregunta: ¿qué features pesan más en la predicción de la tarifa?
-- Resultado esperado: trip_distance en primer lugar, seguida de rate_code_imp
-- y las zonas (hipótesis: la tarifa base depende sobre todo de la distancia y
-- del tipo de tarifa).
-- -----------------------------------------------------------------------------

-- [V4]
SELECT feature, attribution
FROM ML.GLOBAL_EXPLAIN(MODEL `ss2-g16-proyecto2.p2_b_ml.m_fare_linreg`)
ORDER BY attribution DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- V5: explicación global de M-3 (10 features con mayor atribución).
-- Pregunta: ¿qué features pesan más en la probabilidad de propina alta?
-- Resultado esperado: sin hipótesis fuerte; se espera que las zonas y la
-- distancia aparezcan arriba. is_eval no debe aparecer.
-- -----------------------------------------------------------------------------

-- [V5]
SELECT feature, attribution
FROM ML.GLOBAL_EXPLAIN(MODEL `ss2-g16-proyecto2.p2_b_ml.m_tip_logreg`)
ORDER BY attribution DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- V6: bytes procesados y facturados de los tres CREATE MODEL.
-- Pregunta: ¿cuánto costó entrenar cada modelo, en bytes facturados?
-- Ubica los trabajos por el prefijo determinístico de --job_id. Se reportan
-- bytes y no dólares: la tarifa por TB de la creación de modelos no está
-- verificada en la página oficial de precios.
-- Resultado esperado: 3 trabajos en estado DONE, sin error, con
-- statement_type CREATE_MODEL y bytes facturados del orden de la tabla de
-- features (246,198,387 bytes en 11_features.txt) o menos.
-- -----------------------------------------------------------------------------

-- [V6]
SELECT
  job_id,
  statement_type,
  state,
  error_result.reason AS error_reason,
  total_bytes_processed,
  total_bytes_billed,
  total_slot_ms,
  TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_s
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 DAY)
  AND STARTS_WITH(job_id, 'p2_bqml_m')
ORDER BY job_id;
