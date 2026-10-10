# Proyecto dbt SG-Food

Este proyecto dbt fue inicializado por el **Rol A** como esqueleto base para el **Rol B** (transformación y modelado dimensional).

## Estructura del proyecto

```text
dbt_project/
├── dbt_project.yml              # Configuración general y materializaciones por carpeta
├── profiles.yml                 # Perfil de conexión a PostgreSQL usando variables de entorno DW_*
├── README.md                    # Esta guía
├── macros/
│   └── generate_schema_name.sql # Macro que respeta exactamente los schemas staging y marts
└── models/
    ├── staging/
    │   ├── _fuentes.yml         # Declaración de las 12 fuentes cargadas en raw
    │   ├── _staging.yml         # Pruebas de unicidad y no-nulidad del modelo de ejemplo
    │   └── stg_oltp__sucursal.sql # Modelo de ejemplo de staging
    ├── intermediate/            # Modelos intermedios (vacío para Rol B)
    └── marts/                   # Tablas dimensionales y de hechos (vacío para Rol B)
```

## Componentes base y decisiones abiertas para Rol B

| Componente | Qué provee Rol A | Qué decide Rol B |
|------------|------------------|------------------|
| `profiles.yml` | Conexión a `sgfood_dw` con `env_var` (`DW_HOST`, `DW_PORT`, `DW_DB`, `DW_USER`, `DW_PASSWORD`). | Agregar targets adicionales o hilos si se requiere. |
| `macros/generate_schema_name.sql` | Evita que dbt cree schemas compuestos como `staging_staging` o `public_staging`, escribiendo directamente en `staging` y `marts`. | Mantener o ajustar si requiere schemas por desarrollador. |
| `models/staging/_fuentes.yml` | Declaración de las 12 tablas de `raw` con sus columnas según el contrato. | Agregar descripciones de columnas, tests de fuentes y freshness. |
| `models/staging/stg_oltp__sucursal.sql` | Modelo de ejemplo que consume `source('oltp', 'sucursal')`, convierte `id_sucursal` a entero de forma tolerante y proyecta atributos. | Mantenerlo, modificarlo o eliminarlo; agregar el resto de modelos staging. |
| `models/intermediate/` | Carpeta vacía, materializada como vista y **sin schema asignado**. | Decidir en qué schema vive y su materialización; crear los modelos. |
| `models/marts/` | Carpeta vacía configurada como `materialized: table`. | Modelar dimensiones, hechos y marts de negocio. |

## Dos cosas que conviene saber antes de empezar

**Los modelos de `intermediate` hoy se crearían en `public`.** El perfil usa `public` como schema base y la carpeta `intermediate` no tiene `+schema` en `dbt_project.yml`. Quedó así a propósito, porque dónde vive esa capa es una decisión del Rol B. Para enviarla a `staging`, o a un schema propio, basta con agregar `+schema: <nombre>` bajo `intermediate`. Si el schema es nuevo, dbt lo crea.

**Las conversiones de tipo deben tolerar valores inválidos.** `raw` entrega todo como `TEXT`. Un `::int` directo detiene el modelo completo ante un solo valor malo. El modelo de ejemplo muestra el patrón recomendado: convertir solo si el texto tiene la forma esperada y dejar `NULL` en caso contrario, para que lo detecte una prueba `not_null`.

```sql
CASE WHEN id_sucursal ~ '^[0-9]+$' THEN id_sucursal::int END AS id_sucursal
```

## Cómo ejecutar dbt

### 1. Desde dentro del contenedor de Airflow (recomendado)

```bash
docker compose exec airflow-scheduler /opt/dbt-venv/bin/dbt debug --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
docker compose exec airflow-scheduler /opt/dbt-venv/bin/dbt run --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
docker compose exec airflow-scheduler /opt/dbt-venv/bin/dbt test --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
```

### 2. Desde el host (con dbt-postgres instalado en venv local)

Configurar las variables de entorno o crear un `.env`:
- `DW_HOST=localhost`
- `DW_PORT=5433`
- `DW_DB=sgfood_dw`
- `DW_USER=dw_user`
- `DW_PASSWORD=...`

Y ejecutar:
```bash
dbt run --project-dir Proyecto1/dbt_project --profiles-dir Proyecto1/dbt_project
```
