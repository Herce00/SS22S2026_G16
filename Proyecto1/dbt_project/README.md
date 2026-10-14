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
├── models/
    ├── staging/
    │   ├── _fuentes.yml         # Declaración de las 12 fuentes cargadas en raw
    │   ├── _staging.yml         # Descripciones y pruebas de calidad
    │   ├── stg_oltp__sucursal.sql
    │   ├── stg_oltp__categoria.sql
    │   ├── stg_oltp__marca.sql
    │   ├── stg_oltp__producto.sql
    │   ├── stg_oltp__cliente.sql
    │   ├── stg_oltp__venta.sql
    │   ├── stg_oltp__venta_detalle.sql
    │   ├── stg_archivos__inventario_bodega.sql
    │   ├── stg_archivos__proveedores_precios.sql
    │   ├── stg_archivos__devoluciones.sql
    │   ├── stg_archivos__metas_ventas.sql
    │   └── stg_archivos__promociones.sql
    ├── intermediate/
    │   ├── _intermediate.yml
    │   ├── int_ventas_linea.sql
    │   ├── int_inventario_snapshot.sql
    │   ├── int_devoluciones.sql
    │   ├── int_metas_ventas.sql
    │   └── int_precios_proveedor.sql
    └── marts/
        ├── _marts.yml
        ├── dim_fecha.sql
        ├── dim_sucursal.sql
        ├── dim_cliente.sql
        ├── dim_categoria.sql
        ├── dim_marca.sql
        ├── dim_producto.sql
        ├── dim_promocion.sql
        ├── fct_ventas_linea.sql
        ├── fct_inventario_snapshot.sql
        ├── fct_devoluciones.sql
        ├── fct_metas_ventas.sql
        └── fct_precios_proveedor.sql
└── tests/
    └── assert_ventas_subtotal_consistente.sql
```

La capa `staging` contiene actualmente 12 vistas, una por cada fuente de `raw`. No realiza joins: únicamente selecciona las columnas, limpia cadenas y convierte valores desde `TEXT` a `INTEGER`, `BIGINT`, `NUMERIC`, `DATE` o `BOOLEAN` cuando el formato es válido.

## Componentes base y decisiones abiertas para Rol B

| Componente | Qué provee Rol A | Qué decide Rol B |
|------------|------------------|------------------|
| `profiles.yml` | Conexión a `sgfood_dw` con `env_var` (`DW_HOST`, `DW_PORT`, `DW_DB`, `DW_USER`, `DW_PASSWORD`). | Agregar targets adicionales o hilos si se requiere. |
| `macros/generate_schema_name.sql` | Evita que dbt cree schemas compuestos como `staging_staging` o `public_staging`, escribiendo directamente en `staging` y `marts`. | Mantener o ajustar si requiere schemas por desarrollador. |
| `models/staging/_fuentes.yml` | Declaración de las 12 tablas de `raw` con sus columnas según el contrato. | Agregar descripciones de columnas, tests de fuentes y freshness. |
| `models/staging/*.sql` | 12 modelos que consumen las fuentes `oltp` y `archivos`, convierten tipos y limpian valores sin hacer joins. | Mantener las convenciones al agregar transformaciones. |
| `models/staging/_staging.yml` | Descripciones y pruebas `unique`, `not_null` y `accepted_values` para staging. El catálogo de `canal` incluye `Tienda`, `Televenta`, `Mayorista` y `Web`. | Ampliar pruebas cuando se agreguen reglas de calidad. |
| `models/intermediate/` | Cinco vistas con joins y lógica reutilizable; materializadas en `staging`. | Mantener la lógica reutilizable antes de los marts. |
| `models/marts/` | Siete dimensiones y cinco hechos materializados como tablas en `marts`, con pruebas de claves y relaciones. | Mantener pruebas y agregar modelos si aparecen nuevos procesos. |

## Dos cosas que conviene saber antes de empezar

**Los modelos de `intermediate` se crean en `staging`.** La configuración de `dbt_project.yml` asigna `+schema: staging` y `+materialized: view`, de modo que la lógica intermedia queda separada conceptualmente por carpeta, pero reutilizable dentro del schema de preparación.

**Las conversiones de tipo deben tolerar valores inválidos.** `raw` entrega todo como `TEXT`. Un `::int` directo detiene el modelo completo ante un solo valor malo. El modelo de ejemplo muestra el patrón recomendado: convertir solo si el texto tiene la forma esperada y dejar `NULL` en caso contrario, para que lo detecte una prueba `not_null`.

```sql
CASE WHEN id_sucursal ~ '^[0-9]+$' THEN id_sucursal::int END AS id_sucursal
```

## Estado actual de la implementación

| Capa | Estado | Materialización | Schema |
|------|--------|-----------------|--------|
| `raw` | Implementada por Rol A | Tablas | `raw` |
| `staging` | Implementada: 12 modelos con pruebas | Vistas | `staging` |
| `intermediate` | Implementada: 5 modelos con pruebas | Vistas | `staging` |
| `marts` | Implementada: dimensiones y hechos con pruebas | Tablas | `marts` |

## Validar staging

Desde la carpeta `Proyecto1`, con Docker levantado y los datos cargados en `raw`:

```powershell
docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt ls `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project `
  --select path:models/staging

docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt compile `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project `
  --select path:models/staging

docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt build `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project `
  --select path:models/staging
```

El resultado esperado es que se reconozcan 12 modelos, compilen correctamente y las pruebas terminen con estado `PASS`.

## Validar intermediate y marts

```powershell
docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt build `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project `
  --select path:models/intermediate

docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt build `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project `
  --select path:models/marts
```

## Prueba personalizada y documentación

La prueba singular `tests/assert_ventas_subtotal_consistente.sql` valida que cada subtotal sea igual al importe bruto menos el descuento, con tolerancia de un centavo.

Para generar la documentación navegable:

```powershell
docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt docs generate `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project
```

Las descripciones se mantienen en [_staging.yml](models/staging/_staging.yml), [_intermediate.yml](models/intermediate/_intermediate.yml) y [_marts.yml](models/marts/_marts.yml).

`fct_ventas_linea` es la excepción: se materializa como `incremental` con `id_detalle` como clave única para no reconstruir todas las líneas en cada ejecución.

## Validar intermediate

Para validar la capa intermedia completa:

```powershell
docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt build `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project `
  --select path:models/intermediate
```

Los cinco modelos deben compilar y sus pruebas deben finalizar con estado `PASS`.

## Validar marts

Para construir la capa dimensional completa, incluyendo sus dependencias:

```powershell
docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt build `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project `
  --select path:models/marts
```

El selector `path:models/marts` ejecuta los modelos de marts y sus dependencias en orden. La ejecución correcta debe crear siete dimensiones, cinco hechos y finalizar las pruebas con estado `PASS`.

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
