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
| M1 | Dos modelos de familias distintas: regresión lineal para `fare_amount` (`m_fare_linreg`) y regresión logística para "deja propina" (`m_tip_logreg`) | Dos regresiones | Así se cubren las dos familias de métricas que pide el enunciado: RMSE/MAE/R² y ROC-AUC/matriz de confusión. |
| M2 | Solo features conocidas al **inicio** del viaje: `pickup_hour`, `pickup_dow`, `pickup_month`, `trip_distance`, `passenger_count` (imputado), zonas y boroughs de origen y destino, `vendor_id`, `rate_code` | Usar todas las columnas | `trip_duration_min`, `total_amount`, `tip_amount` y `tolls_amount` solo se conocen al terminar el viaje. Incluirlas sería leakage. |
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
| T2 | `Proyecto_2/sql/b_01_features.sql`: `p2_b_ml.features_trips` (muestra, features de M2, imputación de M6, etiquetas `fare_amount` y `is_tipped`, columna `split_set` train/eval/new). Evidencia `11_features.txt`: filas por split, nulos y balance de la etiqueta | Writer delegado. Disparador: SQL no trivial con ejecución y evidencia | [x] |
| T3 | `Proyecto_2/sql/b_02_modelos.sql`: `m_fare_linreg` (RANDOM + `data_split_eval_fraction`), `m_fare_linreg_l2` (variante de hiperparámetros: `l2_reg` y `max_iterations`) y `m_tip_logreg` (CUSTOM temporal). Evidencia `12_modelos.txt` con `ML.TRAINING_INFO` (iteraciones y pérdida) | Writer delegado (el mismo) | [ ] |
| T4 | `Proyecto_2/sql/b_03_evaluacion.sql`: `ML.EVALUATE` sobre octubre para los 3 modelos, `ML.CONFUSION_MATRIX` y `ML.ROC_CURVE` de la logística, y la comparación entre modelos. Evidencia `13_evaluacion.txt` | Writer delegado (el mismo) | [ ] |
| T5 | `Proyecto_2/sql/b_04_predicciones.sql`: `ML.PREDICT` sobre noviembre hacia `pred_fare_nov` y `pred_tip_nov`, más un resumen real contra predicho. Evidencia `14_predicciones.txt` | Writer delegado (el mismo) | [ ] |
| T6 | Sección 8.1 del README, con modelos, leakage y métricas reales | Writer delegado (el mismo) | [ ] |

## Criterios de aceptación

| ID | Criterio |
|----|----------|
| T1 | Plan y D8 en un commit. |
| T2 | La tabla tiene al menos 1M de filas. Cada split tiene filas. No quedan nulos en las features tras la imputación. `is_tipped` solo existe para pagos con tarjeta. |
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
| T2 | Este commit | `11_features.txt`: 2,486,815 filas (train 2,013,181, eval 250,744, new 222,890); 0 nulos en las 11 features; `is_tipped` solo con tarjeta (96.39 % con propina); 50 filas con `fare_amount` > 300 excluidas (p99.99 = 216) | Pendiente de `assess` |

## Siguiente paso

T3: modelos `m_fare_linreg`, `m_fare_linreg_l2` y `m_tip_logreg` sobre `p2_b_ml.features_trips`.
