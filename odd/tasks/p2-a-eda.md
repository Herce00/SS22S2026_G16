# p2-a-eda — Análisis exploratorio y vistas para el tablero (Persona A)

## Objetivo

Responder con SQL las preguntas exploratorias del enunciado (métricas descriptivas, distribuciones categóricas y patrones temporales de viaje, costo y comportamiento) y publicar las vistas `v_eda_*` que alimentan las 3 o más visualizaciones exploratorias del tablero.

## Problema y motivo

| Tema | Detalle |
|------|---------|
| Problema | El enunciado exige consultas SQL avanzadas (agregadas, temporales, filtros, agrupaciones y transformaciones), hallazgos relevantes en el README y al menos 3 visualizaciones exploratorias en Looker Studio o Google Sheets. |
| Motivo | B construye el tablero después de que A termine: las vistas `v_eda_*` le entregan los datos listos, con nombres legibles y sin que tenga que reescribir la lógica. |

## Decisiones

| # | Decisión | Alternativa descartada | Razón |
|---|----------|------------------------|-------|
| E1 | La EDA lee de `p2_a_trips.trips_2022_opt`, la tabla propia de A | Leer de `v_trips_clean` | Es el mismo contenido (huella idéntica, ver `06_contrato_fase2.txt`), pero el contrato es la interfaz de B. A consulta su propia tabla. |
| E2 | Los nombres de zona y borough vienen de `bigquery-public-data.new_york_taxi_trips.taxi_zone_geom` (263 zonas, en `US`) | Mostrar `location_id` crudo | Los gráficos deben ser legibles. La tabla está en la misma región. |
| E3 | Los códigos de `payment_type` y `rate_code` se traducen con `CASE` según el diccionario de datos de TLC. El valor `0` (1,169,077 viajes, fuera de los códigos oficiales 1 a 6) se etiqueta como "Sin código (0)" y se investiga | Descartar las filas con código `0` | Descartarlas ocultaría un hallazgo. No se inventa su significado: solo se reporta lo que muestran los datos. |
| E4 | El análisis de propinas usa solo pagos con tarjeta (`payment_type = '1'`) | Promediar sobre todos los viajes | Las propinas en efectivo no se registran; incluirlas sesgaría la tasa de propina hacia cero. Esta afirmación se verifica con los datos antes de usarla. |
| E5 | Las vistas `v_eda_*` son vistas sobre `opt`, no tablas materializadas | Materializar con `CREATE TABLE` | Son pocas consultas desde el tablero, `opt` ya está optimizada y una vista no queda desactualizada. Se revisa el costo de cada vista con un dry run. |

## Alcance

| Incluido | Fuera de alcance |
|----------|------------------|
| SQL de EDA descriptiva, categórica y temporal, con evidencia | El tablero en Looker Studio (B) |
| 4 vistas `v_eda_*` en `p2_a_trips` | Las secciones del README (feature siguiente) |
| Un resumen de hallazgos con cifras reales, en el archivo de evidencia | Capturas de pantalla de la consola |

## Restricciones

- Proyecto `ss2-g16-proyecto2`, configuración `ss2-p2`, región `US`. La ejecución sigue [conventions.md](../../Proyecto_2/specs/steering/conventions.md).
- Se hace un dry run antes de cada consulta. Una pasada completa por `opt` cuesta como máximo 4.6 GB.
- No se inventan cifras ni interpretaciones: cada hallazgo cita la consulta y la salida que lo sostiene.
- Commits con el formato `<tipo>: <descripción en español ≤50>`, sin alcance ni trailers.

## Entrega

| Atributo | Valor |
|----------|-------|
| Estrategia | `ask-on-risk`; un único PR al final, que abre el usuario |
| Pronóstico | Entre 600 y 800 líneas, sobre todo SQL y evidencia |
| Rama | `feat/p2-a-datos` |

## Tareas

| ID | Tarea | Ruta de ejecución | Estado |
|----|-------|-------------------|--------|
| T1 | Este plan | Inline: un documento | [x] `cb438ac` |
| T2 | `Proyecto_2/sql/a_03_eda_descriptiva.sql`: volumen, `AVG`, `STDDEV` y percentiles (`APPROX_QUANTILES`) de distancia, duración, tarifa, propina y total, y velocidad media derivada. Evidencia `07_eda_descriptiva.txt` | Writer delegado. Disparador: SQL no trivial con ejecución y evidencia | [x] |
| T3 | `Proyecto_2/sql/a_04_eda_categorica.sql`: distribución por `payment_type` (incluida la investigación del código `0`), `rate_code`, `passenger_count` y `vendor_id`; top 10 de zonas de origen y destino con nombre y borough; tasa de propina con tarjeta. Evidencia `08_eda_categorica.txt` | Writer delegado (el mismo) | [x] |
| T4 | `Proyecto_2/sql/a_05_eda_temporal.sql`: viajes e ingreso por hora, día de la semana y mes; matriz hora × día; tendencia diaria con media móvil de 7 días (función de ventana); velocidad media por hora. Evidencia `09_eda_temporal.txt` | Writer delegado (el mismo) | [x] |
| T5 | `Proyecto_2/sql/a_06_vistas_eda.sql`: `v_eda_tendencia_diaria`, `v_eda_hora_dia`, `v_eda_zonas` y `v_eda_pagos`, con el dry run de cada una. Evidencia `10_vistas_eda.txt` con un resumen de hallazgos | Writer delegado (el mismo) | [ ] |

## Criterios de aceptación

| ID | Criterio |
|----|----------|
| T1 | El plan está en un commit. |
| T2 | Cada métrica tiene su salida real guardada. Los percentiles muestran la cola (p95, p99) además de la mediana. |
| T3 | Las distribuciones suman 34,796,108 filas. El código `0` queda caracterizado con datos (por ejemplo, su relación con `passenger_count` nulo y con `rate_code`). La afirmación de E4 queda verificada o refutada con datos. |
| T4 | Los patrones por hora, día y mes tienen su salida real. La media móvil usa `AVG(...) OVER (ORDER BY ... ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)`. |
| T5 | Las 4 vistas existen en `p2_a_trips`, tienen columnas legibles y un costo por consulta medido. El resumen de hallazgos cita la evidencia de cada cifra. |

## Verificación

| Tema | Regla |
|------|-------|
| Test-first | Excepción: no hay emulador local de BigQuery. La verificación es el dry run, la ejecución, la evidencia guardada y controles de consistencia, como que las distribuciones sumen el total de filas. |
| Revisión nativa | `gentle-ai review assess --base-ref 78d37a2 --committed-only` sobre cada commit. Si pide consentimiento, se le presenta al usuario. |

## Progreso y evidencia

| ID | Commit | Evidencia | Revisión |
|----|--------|-----------|----------|
| T2 | `a1b9a4e` | `07_eda_descriptiva.txt`: 34,796,108 viajes en 335 días (2022-01-01 a 2022-12-01), ingreso USD 747,517,061.02; mediana de distancia 1.91 mi (p99 20.18), de total USD 15.96 (p99 79.62); velocidad mediana 10.38 mph y 2,306 viajes > 80 mph; 68.92 % de viajes < 3 mi; tarifa por milla de 8.77 a 2.76 USD/mi; 1,169,077 nulos en `passenger_count` (3.36 %). Controles D1 y D4 = 34,796,108 | `medium` / `slice_budget_reached` → consentimiento declinado por el usuario (solo este candidato); el siguiente tramo parte de `a1b9a4e` |
| T3 | `6e78d57` | `08_eda_categorica.txt`: tarjeta 76.74 %, efectivo 19.46 %, código 0 3.36 %; el código 0 son los mismos 1,169,077 viajes con `passenger_count` y `rate_code` nulos, y el 89.79 % de ellos registra propina; el 99.99 % de la tarifa JFK es USD 52 (hipótesis de T2 confirmada); JFK Airport es la zona de origen número 1 (4.74 %); Manhattan es el origen del 89.50 %; 447,026 orígenes sin zona (264, 265, 57 y 105); E4 verificada (efectivo con propina 0.01 %), tasa de propina con tarjeta p50 26.40 %. Controles C1, C4 y C7 = 34,796,108 | `medium` / `slice_budget_reached` → consentimiento declinado por el usuario (solo este candidato); el siguiente tramo parte de `6e78d57` |
| T4 | Este commit | `09_eda_temporal.txt`: pico de demanda a las 18:00 (7.12 %, 2,477,600 viajes), valle a las 04:00 (0.54 %); velocidad media mínima a las 16:00 (10.32 mph) y máxima a las 05:00 (21.38 mph); jueves día pico anual en volumen (15.31 %, 5,327,628 viajes) y viernes en promedio diario (111,914.1 viajes/día); domingo menor demanda (12.14 %) pero mayor velocidad (14.30 mph) y mayor ticket (USD 22.24); crecimiento acelerado feb (+21.08 %) y mar (+21.74 %), pico en oct (3,516,529 viajes); hora punta a las 18:00 en 6 de 7 días (domingo a las 17:00); martes 18:00 combinación más demandada del año (390,043 viajes, rank 1); mínimo histórico anual por ventisca el 2022-01-29 (33,007 viajes); días hábiles 73.29 % de demanda vs 26.71 % fin de semana (velocidad +14.1 % fin de semana); tasa mediana propina con tarjeta entre 25.56 % y 27.27 %, con no-propina de 2.97 % a las 18:00 vs 8.67 % a las 04:00. Controles T1, T2, T3, T6 = 34,796,108 y T7 = 26,703,778 | Pendiente |

## Siguiente paso

T5: Vistas de visualización `v_eda_*` (`a_06_vistas_eda.sql`) y evidencia 10 con resumen consolidado de hallazgos.
