# p2-a-bqml — Features, modelos BigQuery ML, evaluación y predicciones (reasignado a Persona A)

## Objetivo

Entrenar y comparar al menos 2 modelos de BigQuery ML sobre un dataset limpio, controlando el data leakage, y ejecutar predicciones sobre registros nuevos. Las métricas deben ser reales para que el tablero de B use datos verificados.

## Problema y motivo

| Tema | Detalle |
|------|---------|
| Problema | El enunciado exige al menos 2 modelos de regresión o clasificación comparados con métricas e hiperparámetros distintos (ROC-AUC, RMSE, matriz de confusión, iteraciones), manejo de leakage con `data_split_eval_fraction` y un split personalizado, y predicciones sobre registros nuevos. |
| Motivo | La decisión D8 del steering reasigna este trabajo a A. B conserva el tablero, el "Rolling Forecast", las vistas `v_dash_*`, la sección 8.2 del README y las capturas. |

## Decisiones

| # | Decisión | Alternativa descartada | Razón |
|---|----------|------------------------|-------|
| M1 | Dos modelos de familias distintas: regresión lineal para `fare_amount` (`m_fare_linreg`) y regresión logística para "propina alta" (`m_tip_logreg`, etiqueta `is_high_tip` = `tip_amount / fare_amount >= 0.25`, solo con tarjeta). `is_tipped` queda en la tabla solo como referencia | Dos regresiones; logística sobre `is_tipped` | Así se cubren las dos familias de métricas que pide el enunciado: RMSE/MAE/R² y ROC-AUC/matriz de confusión. `is_tipped` es positivo en el 96.40 % de los viajes con tarjeta: un modelo que siempre dice "sí" ya tiene 96 % de exactitud y la matriz de confusión y la precisión no informan nada. `is_high_tip` queda en 60.01 % (V6 de `11_features.txt`). |
| M2 | Solo features conocidas al **inicio** del viaje: `pickup_hour`, `pickup_dow`, `trip_distance`, `passenger_count` (imputado), zonas y boroughs de origen y destino, `vendor_id`, `rate_code`. `pickup_month` queda en la tabla **solo para el split**; no es input de ningún modelo | Usar todas las columnas; usar `pickup_month` como feature | `trip_duration_min`, `total_amount`, `tip_amount` y `tolls_amount` solo se conocen al terminar el viaje. Incluirlas sería leakage. El entrenamiento cubre los meses 1 a 9: los meses 10 y 11 nunca se ven al entrenar y el modelo extrapolaría. |
| M3 | El modelo de propina usa solo pagos con tarjeta (`payment_type = '1'`) y excluye `payment_type` como feature | Entrenar con todos los pagos | En efectivo la propina no se registra (0.01 % con propina, `08_eda_categorica.txt`). Con todos los pagos, el modelo aprendería "efectivo = sin propina". |
| M4 | Split, con los dos mecanismos del enunciado: `m_fare_linreg` usa `data_split_method='RANDOM'` con `data_split_eval_fraction`; `m_tip_logreg` usa `data_split_method='CUSTOM'` con una columna booleana temporal. En ambos, el entrenamiento cubre ene–sep, la evaluación de retención es octubre y los "nuevos registros" son noviembre (opción A del steering) | Un único split aleatorio | El split temporal evita el leakage del futuro hacia el pasado, y octubre queda como prueba que ningún modelo vio. |
| M5 | Muestra determinística con `MOD(trip_id, 14) = 0`, de unos 2 a 3 millones de filas. Sin `ABS`: `FARM_FINGERPRINT` puede devolver el mínimo de INT64 y `ABS` desborda con ese valor | Entrenar con 34.8M filas | Crear modelos lineales o logísticos cuesta unos USD 250 por TB (fuente de terceros, sin verificar en la página oficial). La muestra cumple el mínimo de 1M y mantiene el costo bajo. Cada `CREATE MODEL` lleva dry run previo. |
| M6 | Imputación: `passenger_count` NULL pasa a 1 y se agrega la marca `passenger_missing`. `rate_code` NULL pasa a `'NA'` | Descartar las filas | Los nulos son el bloque cerrado del código 0 (1,169,077 filas); descartarlo sesgaría el modelo. |
| M7 | Zonas con `SELECT DISTINCT zone_id, zone_name, borough` sobre `taxi_zone_geom` | Join directo | La tabla tiene `zone_id` duplicados (260 distintos en 263 filas). |

## Alcance

| Incluido | Fuera de alcance (B, ver D8) |
|----------|------------------------------|
| `p2_b_ml.features_trips` con columna de split | Tablero de Looker Studio |
| 2 modelos y por lo menos 1 variante de hiperparámetros | Comparación "Rolling Forecast" (pendiente de la consulta al auxiliar) |
| `ML.EVALUATE`, `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.TRAINING_INFO` | Vistas `v_dash_*` |
| `ML.PREDICT` sobre noviembre en tablas `pred_*` | Sección 8.2 del README y capturas |
| Sección 8.1 del README con cifras reales | |

## Restricciones

- Proyecto `ss2-g16-proyecto2`, configuración `ss2-p2`, región `US`. Ejecución según [conventions.md](../../Proyecto_2/specs/steering/conventions.md).
- Fuente: `p2_contract.v_trips_clean`. Es la interfaz de datos del ML y sigue la ruta B del flujo, aunque ahora la ejecute A.
- Dry run antes de cada sentencia. Hay que parar y avisar si un `CREATE MODEL` estima más de 10 GB.
- No se inventan métricas: cada cifra sale de una salida guardada.
- Commits: `<tipo>: <descripción en español ≤50>`, sin alcance ni trailers.

## Entrega

| Atributo | Valor |
|----------|-------|
| Estrategia | `ask-on-risk`. PR único al final, lo abre el usuario |
| Pronóstico | Unas 600 a 900 líneas (SQL, evidencia y README) |
| Rama | `feat/p2-a-datos` |

## Tareas

| ID | Tarea | Ruta de ejecución | Estado |
|----|-------|-------------------|--------|
| T1 | Este plan y la decisión D8 en el steering | Inline: dos documentos con cambios chicos | [x] `75db3e9` |
| T2 | `Proyecto_2/sql/b_01_features.sql`: `p2_b_ml.features_trips` (muestra, features de M2, imputación de M6, etiquetas `fare_amount`, `is_high_tip` e `is_tipped` de referencia, columna `split_set` train/eval/new, sin los días con datos faltantes en la fuente). Evidencia `11_features.txt`: filas por split, días excluidos, nulos y balance de las etiquetas | Writer delegado. Disparador: SQL no trivial con ejecución y evidencia | [x] |
| T3 | `Proyecto_2/sql/b_02_modelos.sql`: `m_fare_linreg` (RANDOM + `data_split_eval_fraction`, optimizador por defecto), `m_fare_linreg_gd` (variante de hiperparámetros: `BATCH_GRADIENT_DESCENT`, `l2_reg`, `max_iterations`, `LINE_SEARCH`, `early_stop`; antes llamada `m_fare_linreg_l2`) y `m_tip_logreg` (CUSTOM temporal). Evidencia `12_modelos.txt` con `ML.TRAINING_INFO` (iteraciones y pérdida), `ML.FEATURE_INFO` (leakage), `ML.GLOBAL_EXPLAIN` y bytes de cada trabajo | Writer delegado (el mismo) | [x] |
| T4 | `Proyecto_2/sql/b_03_evaluacion.sql`: `ML.EVALUATE` sobre octubre para los 3 modelos, `ML.CONFUSION_MATRIX` y `ML.ROC_CURVE` de la logística, y la comparación entre modelos, más baselines (media, tarifa por milla, clase mayoritaria), repetición sobre noviembre y diagnóstico de pesos de M-1 (`ML.WEIGHTS`). Evidencia `13_evaluacion.txt` | Writer delegado (el mismo) | [x] |
| T5 | `Proyecto_2/sql/b_04_predicciones.sql`: `ML.PREDICT` sobre noviembre hacia `pred_fare_nov` y `pred_tip_nov`, más un resumen real contra predicho. Evidencia `14_predicciones.txt` | Writer delegado (el mismo) | [x] |
| T6 | Sección 8.1 del README, con modelos, leakage y métricas reales | Writer delegado (el mismo) | [ ] |

## Criterios de aceptación

| ID | Criterio |
|----|----------|
| T1 | Plan y D8 en un commit. |
| T2 | La tabla tiene al menos 1M de filas. Cada split tiene filas. No quedan nulos en las features tras la imputación. `is_tipped` e `is_high_tip` solo existen para pagos con tarjeta. Se excluyen solo los días que marca la regla horaria (2022-09-17 y 2022-09-18). |
| T3 | Los 3 modelos existen. `ML.TRAINING_INFO` muestra iteraciones y pérdida. La variante difiere en hiperparámetros documentados. |
| T4 | Métricas reales sobre octubre: RMSE, MAE y R² de las regresiones; ROC-AUC, precisión, recall y matriz de confusión de la logística. Hay una conclusión de qué modelo rinde mejor y por qué, con las hipótesis marcadas. |
| T5 | Las tablas `pred_*` cubren noviembre y hay una comparación agregada entre valores reales y predichos. |
| T6 | La sección 8.1 cita solo cifras de la evidencia. La 8.2 sigue reservada para B. |

## Verificación

| Tema | Regla |
|------|-------|
| Test-first | Excepción: no hay emulador local de BigQuery. La verificación es dry run, ejecución, evidencia guardada y controles de consistencia (filas por split que suman el total de la muestra). |
| Revisión nativa | `gentle-ai review assess --base-ref 6e78d57 --committed-only` por commit. El usuario prefiere revisar al final: si se pide consentimiento, se le presenta y él decide. |

## Progreso y evidencia

| ID | Commit | Evidencia | Revisión |
|----|--------|-----------|----------|
| T2 | `e837b56`; tabla recreada en este commit (`is_high_tip` y exclusión de días anómalos) | `11_features.txt`: 2,482,519 filas (train 2,008,885, eval 250,744, new 222,890); V0 excluye 2022-09-17 y 2022-09-18 (4,296 filas de la muestra); 0 nulos en las 11 features; `is_tipped` solo con tarjeta (96.40 % con propina, referencia); V6 `is_high_tip` 60.01 % TRUE (train 60.28 %, eval 58.73 %, new 59.03 %; train 0.28 puntos sobre el 60 % esperado, umbral sin ajustar); 50 filas con `fare_amount` > 300 excluidas (p99.99 = 216) | aprobada en `review-5cb79f936ff5075f` (tramo hasta `e837b56`) |
| T3 | `66a231e` | `12_modelos.txt`: los 3 modelos creados (trabajos `p2_bqml_m1_1792977147`, `p2_bqml_m2_1792977195`, `p2_bqml_m3_1792977428`, DONE). Dry run 192,737,539 / 192,737,539 / 177,265,140 bytes; facturados 564,133,888 bytes en total. M-1: AUTO_STRATEGY eligió `NORMAL_EQUATION`, 1 iteración, loss 13.05 y eval_loss 124.35 (hallazgo: probable colinealidad zona/borough y `passenger_missing`/`rate_code_imp = 'NA'` sin L2; T4 lo confirma o descarta). M-2: 20 iteraciones (máximo), loss 85.13 a 15.79, eval_loss 15.98. M-3: 5 iteraciones (early_stop), log-loss 0.6636 a 0.6111, eval_loss 0.6212. V3: 11 features en cada modelo y 0 columnas excluidas; `is_eval` fuera de M-3 | `medium` / `slice_budget_reached` → consentimiento declinado por el usuario (solo este candidato); el siguiente tramo parte de `66a231e` |
| T4 | `3d06cea` | `13_evaluacion.txt` (15 bloques, dry runs entre 43,504 y 212,641,195 bytes; 2,197,915,615 en total). Octubre (250,744 filas): M-1 RMSE 3.93 / R² 0.915, M-2 RMSE 4.32 / R² 0.898, mejor baseline (tarifa por milla) RMSE 12.52 / R² 0.143. Noviembre (222,890): M-1 RMSE 15.27 / R² -0.299 (14 filas concentran el 94 % del SSE; las peores con zonas de origen de 0 o 1 fila en `train`), M-2 RMSE 4.24 / R² 0.900. Pesos de M-1 hasta 20,163 (M-2: 35.97) y colinealidad exacta probada en `train` (E6c). M-3 en octubre (194,093): exactitud 0.666 frente a 0.587 del baseline, ROC-AUC 0.692, log_loss 0.621 frente a 0.678; noviembre igual (0.667, 0.692). Recomendado: M-2 para tarifa | `medium` / `slice_budget_reached` → consentimiento declinado por el usuario (solo este candidato); el siguiente tramo parte de `3d06cea` |
| T5 | Este commit | `14_predicciones.txt` (10 bloques; dry runs entre 0 y una cota superior de 262,546,635 bytes; 565,482,592 en total). `pred_fare_nov` (M-1 y M-2) con 222,890 filas y `pred_tip_nov` con 172,626, `trip_id` único y 0 nulos; 1 fila del 2022-12-01 (día parcial). Métricas recalculadas desde las tablas iguales a noviembre en 13 (M-1 RMSE 15.27 / R² -0.299, M-2 RMSE 4.24 / R² 0.900, M-3 exactitud 0.667). Total del mes: M-2 -3.41 % y M-1 -2.63 % frente al real; M-2 entre -6.34 % y +5.19 % por día y subestima en 27 de 30 días. Las 14 filas extremas de M-1 mueven 3 días entre 1.2 y 4.8 puntos y dominan Staten Island (+1,016.3 %) y el Bronx (+61.58 %); efecto neto en el mes 0.19 %. Vista `v_ml_pred_diaria` creada (31 filas, P5b) | Pendiente de `assess` |

## Siguiente paso

T6: reescribir la sección 8.1 del README con los 3 modelos, el control de leakage, las métricas de octubre y noviembre con baselines, el hallazgo M-1 frente a M-2, el modelo seleccionado, las tablas `pred_*`, la vista diaria y el costo de los `CREATE MODEL`; la 8.2 sigue reservada para B.
