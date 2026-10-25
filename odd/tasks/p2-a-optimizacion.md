# p2-a-optimizacion — Tablas derivadas, particiones, clustering y fase 2 del contrato (Persona A)

## Objetivo

Crear las tablas derivadas de A, una estándar y una optimizada (particionada por fecha y con clustering por ubicaciones), demostrar con evidencia la reducción de bytes procesados y pasar el contrato `v_trips_clean` a la fase 2 sin cambiar su esquema.

## Problema y motivo

| Tema | Detalle |
|------|---------|
| Problema | La tabla pública no tiene particiones ni clustering: toda consulta escanea las columnas completas, unos 2.6 GB por consulta en la vista de fase 1. El enunciado exige tablas derivadas en el proyecto propio, particiones por fecha, clustering por ubicaciones y una comparación de rendimiento antes y después. |
| Motivo | La comparación estándar vs optimizada es un entregable obligatorio, y la fase 2 abarata cada consulta de B sobre el contrato. |

## Decisiones

| # | Decisión | Alternativa descartada | Razón |
|---|----------|------------------------|-------|
| O1 | La lógica de limpieza vive en el script que construye `trips_2022_opt` (desde la tabla pública). La vista de fase 2 es una proyección simple sobre `trips_2022_opt`. | Construir `trips_2022_opt` con `SELECT * FROM v_trips_clean` | Si la vista apunta a `opt` y `opt` se construye desde la vista, la reconstrucción queda circular. |
| O2 | `trips_2022_std` se construye como `SELECT * FROM trips_2022_opt`, sin particiones ni clustering. | Repetir el `SELECT` de limpieza | Mismos datos con distinto layout físico: la comparación aísla el efecto de la optimización y no duplica la lógica. |
| O3 | `PARTITION BY DATE(pickup_datetime)` (diaria) y `CLUSTER BY pickup_location_id, dropoff_location_id` | Partición mensual; clustering por `payment_type` | Exigido por el enunciado. Unas 335 particiones diarias, muy por debajo del límite de 10,000. Las ubicaciones son los filtros más selectivos. |
| O4 | Sin `require_partition_filter` | Exigir el filtro de partición | B entrena sobre rangos de meses y debe poder consultar sin errores. |
| O5 | La comparación se ejecuta con `--nouse_cache` y las métricas se leen de `INFORMATION_SCHEMA.JOBS_BY_USER` (`total_bytes_processed`, `total_bytes_billed`, `total_slot_ms`, duración) | Leer solo el dry run | El dry run no refleja la poda por clustering; los bytes reales sí. |

## Alcance

| Incluido | Fuera de alcance |
|----------|------------------|
| `trips_2022_opt`, `trips_2022_std` y la evidencia de sus metadatos | EDA y vistas `v_eda_*` (feature siguiente) |
| Comparación de rendimiento: tabla pública vs `std` vs `opt` | Capturas de pantalla de la consola (feature de README y evidencia) |
| Fase 2 del contrato y nueva validación | Acceso de B (feature final) |

## Restricciones

- Proyecto `ss2-g16-proyecto2`, configuración `ss2-p2`, ubicación `US`. Ejecución según [conventions.md](../../Proyecto_2/specs/steering/conventions.md) (`PYTHONUTF8=1` y `cmd //c`).
- Esquema del contrato congelado: la fase 2 debe dar exactamente las mismas 19 columnas y las mismas 34,796,108 filas.
- Dry run antes de cada consulta nueva; cortar si una consulta supera 10 GB estimados.
- Commits: `<tipo>: <descripción en español ≤50>`, sin alcance ni trailers.

## Entrega

| Atributo | Valor |
|----------|-------|
| Estrategia | `ask-on-risk`; PR único al final, lo abre el usuario |
| Pronóstico | Unas 300 a 400 líneas, en su mayoría SQL y evidencia |
| Rama | `feat/p2-a-datos` |

## Tareas

| ID | Tarea | Ruta de ejecución | Estado |
|----|-------|-------------------|--------|
| T1 | Este plan y el renombre de la rama | Inline: un documento | [x] `8e6be84` |
| T2 | `Proyecto_2/sql/a_01_tablas_derivadas.sql`: `trips_2022_opt` (limpieza, partición y clustering) y `trips_2022_std`. Evidencia de metadatos: filas, bytes, número de particiones y campos de clustering | Writer delegado. Disparador: SQL no trivial con ejecución y evidencia | [x] (commit de T2) |
| T3 | `Proyecto_2/sql/a_02_comparacion_rendimiento.sql`: 3 o 4 consultas representativas sobre la tabla pública, `std` y `opt`, con métricas reales de `JOBS_BY_USER` | Writer delegado (mismo writer) | [ ] |
| T4 | Fase 2 del contrato: `01_v_trips_clean.sql` lee de `trips_2022_opt`; se vuelve a ejecutar `02_validaciones_contrato.sql` y se compara con la fase 1 | Writer delegado (mismo writer) | [ ] |

## Criterios de aceptación

| ID | Criterio |
|----|----------|
| T1 | El plan está en un commit y la rama se llama `feat/p2-a-datos`. |
| T2 | `opt` tiene 34,796,108 filas, partición diaria por `DATE(pickup_datetime)` y clustering `pickup_location_id, dropoff_location_id`. `std` tiene las mismas filas y no tiene particiones ni clustering. Evidencia guardada. |
| T3 | Para cada consulta hay bytes procesados, bytes facturados, slot ms y duración en las tres fuentes. `opt` procesa menos bytes que `std` en las consultas con filtro de fecha o ubicación. Las cifras son reales y están guardadas en evidencia. |
| T4 | La vista de fase 2 devuelve el mismo esquema, las mismas filas y 0 duplicados. Una consulta típica de B procesa menos bytes que en la fase 1. Evidencia guardada. |

## Verificación

| Tema | Regla |
|------|-------|
| Test-first | Excepción: no hay emulador local de BigQuery. La verificación es dry run, ejecución y evidencia guardada; la fase 2 se valida con las mismas consultas de `02_validaciones_contrato.sql`, que hacen de prueba de regresión del contrato. |
| Revisión nativa | `gentle-ai review assess --base-ref bf93421 --committed-only` sobre cada commit. Es probable que el slice llegue a ~400 líneas en T2 o T3 y dispare la revisión. |

## Progreso y evidencia

| ID | Commit | Evidencia | Revisión |
|----|--------|-----------|----------|
| T2 | Commit `feat: crea tablas derivadas std y optimizada` (el hash se anota al cerrar T2) | [04_tablas_derivadas.txt](../../Proyecto_2/evidencia/04_tablas_derivadas.txt): 34,796,108 filas en `opt` y `std`; 4,599,289,734 bytes lógicos (4.28 GiB) en cada una; `opt` con 335 particiones diarias (20220101 a 20221201, sin `__NULL__`) y clustering `pickup_location_id` (1), `dropoff_location_id` (2); `std` sin partición ni clustering; mismo `BIT_XOR(trip_id)` que la vista de fase 1. CTAS: `opt` 4,501,953,419 bytes procesados, `std` 4,599,289,734 | Pendiente de `assess` |

## Siguiente paso

T3: comparación de rendimiento entre la tabla pública, `trips_2022_std` y `trips_2022_opt` (`Proyecto_2/sql/a_02_comparacion_rendimiento.sql`).
