# Arquitectura y contrato de datos — Proyecto 2 (NYC Taxi 2022)

Análisis exploratorio, optimización y BigQuery ML sobre los viajes de taxi amarillo de Nueva York de 2022. Este documento fija quién es dueño de qué, cómo fluyen los datos y el contrato que permite a A y B trabajar en paralelo sin bloquearse.

- **Fuente de requisitos:** [enunciado.md](../../enunciado.md)
- **Documento hermano:** [conventions.md](conventions.md)

## Roles

| Rol | Integrante | Carné | Foco | Prefijo de rama |
|-----|-----------|-------|------|-----------------|
| **A** | Keneth Willard Lopez Ovalle | `202100106` | Datos, EDA, particiones y clustering, comparación de costos | `feat/p2-a-*` |
| **B** | César Rolando Hernández Palacios | `202000806` | BigQuery ML, predicciones, tablero Looker Studio, presentación | `feat/p2-b-*` |

Ambos deben poder explicar el proyecto completo en la calificación.

## Flujo de datos

```
bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022
        │
        ▼
p2_a_trips  (A: copia estándar, copia optimizada, vistas EDA)
        │
        ▼
p2_contract.v_trips_clean  (puerto compartido)
        │
        ▼
p2_b_ml  (B: features, modelos, predicciones, vistas del tablero)
        │
        ▼
Looker Studio
```

## Fuente

| Atributo | Valor verificado (2026-10-25) |
|----------|-------------------------------|
| Tabla | `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022` |
| Ubicación | `US` |
| Filas | 36,256,539 |
| Tamaño | 7,487,651,196 bytes |
| Particiones / clustering | Ninguno |
| Proyecto GCP propio | `ss2-g16-proyecto2` (cuenta USAC de A, crédito de prueba) |

El enunciado indica "más de 100 millones de registros"; la tabla real tiene 36.26 millones. Ver [preguntas abiertas](#preguntas-abiertas).

## Datasets

Todos los datasets se crean en la ubicación `US`. Es obligatorio: la fuente está en `US` y BigQuery no permite consultas entre regiones.

| Dataset | Dueño | Zona | Objetos |
|---------|-------|------|---------|
| `p2_a_trips` | A | Verde para A | `trips_2022_std`: copia derivada sin optimizar (línea base). `trips_2022_opt`: `PARTITION BY DATE(pickup_datetime)`, `CLUSTER BY pickup_location_id, dropoff_location_id`. `v_eda_*`: vistas para las gráficas exploratorias. |
| `p2_contract` | Compartido | Amarilla | `v_trips_clean` |
| `p2_b_ml` | A (ML, ver D8) y B (tablero) | Verde para el dueño de cada objeto | `features_*`, modelos `m_*`, predicciones `pred_*`, vistas del tablero `v_dash_*` |

## Contrato: `p2_contract.v_trips_clean`

Es el mecanismo de desacoplamiento entre A y B.

| Regla | Detalle |
|-------|---------|
| Único punto de lectura | B lee **solo** esta vista, nunca las tablas de `p2_a_trips`. |
| Esquema congelado | Agregar, quitar, renombrar o cambiar el tipo de una columna requiere acuerdo de ambos (zona amarilla). |
| Fase 1 (día 1) | El `FROM` apunta a la tabla pública y aplica los filtros de limpieza. B empieza de inmediato, sin esperar a A. |
| Fase 2 | Cuando A termina `trips_2022_opt`, A cambia el `FROM` a `p2_a_trips.trips_2022_opt` **sin cambiar el esquema**. B no modifica nada. |

**2026-10-25:** la fase 2 está activa. La vista ahora proyecta `p2_a_trips.trips_2022_opt` y el esquema no cambió. Evidencia: `Proyecto_2/evidencia/06_contrato_fase2.txt`.

### Columnas

| Columna | Tipo | Regla |
|---------|------|-------|
| `trip_id` | INT64 | `FARM_FINGERPRINT` sobre `vendor_id`, `pickup_datetime`, `dropoff_datetime`, `pickup_location_id`, `dropoff_location_id`, `trip_distance`, `total_amount`. Determinista; habilita el split personalizado de B. La unicidad debe validarse. |
| `vendor_id` | STRING | |
| `pickup_datetime` | TIMESTAMP | |
| `dropoff_datetime` | TIMESTAMP | |
| `pickup_date` | DATE | |
| `pickup_hour` | INT64 | |
| `pickup_dow` | INT64 | 1 = domingo, igual que `DAYOFWEEK` de BigQuery |
| `pickup_month` | INT64 | |
| `trip_duration_min` | FLOAT64 | |
| `passenger_count` | INT64 | NULLABLE |
| `trip_distance` | FLOAT64 | |
| `rate_code` | STRING | |
| `payment_type` | STRING | |
| `fare_amount` | FLOAT64 | |
| `tip_amount` | FLOAT64 | |
| `tolls_amount` | FLOAT64 | |
| `total_amount` | FLOAT64 | |
| `pickup_location_id` | STRING | |
| `dropoff_location_id` | STRING | |

Las columnas NUMERIC de la fuente se convierten a FLOAT64 para BigQuery ML.

### Filtros de limpieza

Conteos del perfil sobre la tabla completa. Cada conteo es independiente: una fila puede violar varias reglas, así que no se suman.

| Filtro que se conserva | Filas que viola en la fuente |
|------------------------|-----------------------------:|
| `pickup_datetime` en [2022-01-01, 2023-01-01) | 556 (mín. 2001-01-01, máx. 2023-04-18) |
| `dropoff_datetime > pickup_datetime` | 30,368 |
| Duración <= 360 min | 43,297 |
| `trip_distance > 0` | 511,442 (nulo o <= 0) |
| `trip_distance <= 100` | 1,384 |
| `fare_amount > 0` | 241,621 (nulo o <= 0) |
| `total_amount > 0` | 234,038 (nulo o <= 0) |
| `passenger_count` nulo o entre 1 y 6 | 703,499 (0 o > 6) |

- `passenger_count` nulo **se conserva**: son 1,241,840 filas. B decide cómo imputarlo.
- Las ubicaciones no tienen nulos (0 filas). La fuente tiene 6 valores distintos de `payment_type` y 7 de `rate_code`.

### Split temporal propuesto

Es decisión de B; se registra aquí porque depende de las particiones por fecha. A eligió la opción A el 2026-10-25. **Pendiente de confirmación por B.**

| Conjunto | Periodo | Filas en `v_trips_clean` |
|----------|---------|--------------------------|
| Entrenamiento | enero a septiembre de 2022 (`pickup_month` 1–9) | 28,160,489 |
| Evaluación | octubre de 2022 (`pickup_month` = 10) | 3,516,529 |
| Nuevos registros (predicción) | noviembre de 2022 (`pickup_month` >= 11) | 3,119,090 |

La fuente no tiene archivo de diciembre: `data_file_month` solo va de 1 a 11. Las 57 filas con `pickup_month` = 12 son viajes del 2022-12-01 que vienen en el archivo de noviembre, y se asignan a "nuevos registros". Evidencia: `Proyecto_2/evidencia/03_contrato_validaciones.txt`. El split original, que usaba diciembre como nuevos registros, se descartó por esta razón.

## Regla de zonas

| Zona | Significado | Acción |
|------|-------------|--------|
| **Verde** | Ruta propia, sin tocar un tema compartido | Editar libremente |
| **Amarilla** | Tema compartido | Proponer; editar solo con acuerdo del otro integrante |
| **Roja** | Ruta del otro integrante | Solo lectura; cambios por pull request del dueño |

| Ruta | A | B |
|------|---|---|
| `Proyecto_2/sql/a_*` | Verde | Roja |
| `Proyecto_2/sql/b_*` | Roja | Verde |
| `Proyecto_2/sql/contract/` | Amarilla | Amarilla |
| `Proyecto_2/README.md` | Verde en sus secciones, amarilla en las comunes | Verde en sus secciones, amarilla en las comunes |
| `Proyecto_2/evidencia/` | Verde para su propia evidencia y la del contrato; roja para la de B | Verde para su propia evidencia; roja para la de A |
| `Proyecto_2/specs/steering/` | Amarilla | Amarilla |

## Decisiones

| # | Decisión | Alternativa descartada | Motivo |
|---|----------|------------------------|--------|
| D1 | Proyecto GCP dedicado `ss2-g16-proyecto2` en la cuenta USAC de A | Proyecto personal o compartido con otros cursos | Aísla costos y permisos; el crédito de prueba cubre el proyecto. |
| D2 | Ubicación `US` para todos los datasets | Una región cercana, como `us-east1` | La fuente está en `US`; BigQuery no consulta entre regiones. |
| D3 | El contrato es una vista | Una tabla compartida materializada | La vista permite cambiar el origen (fase 1 a fase 2) sin que B toque nada y sin duplicar almacenamiento. |
| D4 | NUMERIC se convierte a FLOAT64 en la vista | Dejar NUMERIC y convertir en cada consulta de B | BigQuery ML trabaja con FLOAT64; se convierte una sola vez. |
| D5 | Conservar `passenger_count` nulo | Descartar esas filas | Se perderían 1,241,840 viajes; la imputación es decisión de modelado de B. |
| D6 | `trip_id` con `FARM_FINGERPRINT` | `ROW_NUMBER()` o `GENERATE_UUID()` | Es determinista entre ejecuciones; un split personalizado reproducible lo requiere. |
| D7 | Specs ligeras: este steering más un documento ODD por feature | Tres archivos SDD por feature (requisitos, diseño, tareas) | El proyecto es corto; la ceremonia extra no aporta. |
| D8 | Reasignación (2026-10-25, decisión de A, **pendiente de confirmar con B**): A construye features, los 2 modelos BQML, la evaluación y las predicciones en `p2_b_ml` (`features_*`, `m_*`, `pred_*`). B conserva el tablero de Looker Studio, la comparación "Rolling Forecast", las vistas `v_dash_*`, la sección 8.2 del README y las capturas | Que B haga todo el ML | B empieza cuando A termina; adelantar el ML con métricas reales le deja a B un tablero con datos ya verificados. B mantiene trabajo propio y visible en el historial. |

## Preguntas abiertas

| # | Pregunta | Responsable | Estado |
|---|----------|-------------|--------|
| Q1 | El enunciado pide "Rolling Forecast" (línea 82), pero también modelos de "regresión o clasificación" (línea 13). ¿Qué se espera exactamente? | Preguntar al auxiliar | Abierta |
| Q2 | Correo de la cuenta Google de B, necesario para darle acceso a BigQuery | B | Pendiente |
| Q3 | El enunciado indica más de 100 millones de filas; la tabla tiene 36,256,539. Documentar la cifra real en el README. | A | Registrada |
