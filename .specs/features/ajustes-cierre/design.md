# Diseño — `ajustes-cierre`

Corrige el proyecto de B sin rediseñarlo: mismos hechos, dimensiones y granos. Cambia cómo se generan las claves, cómo se convierten los tipos, qué se prueba, qué restricciones existen en la base y qué dicen los documentos. Del lado del rol A ordena el servicio pgAdmin y actualiza lo que quedó desactualizado.

- **Requisitos:** [requirements.md](requirements.md)
- **Tareas:** [tasks.md](tasks.md)

## Decisiones de diseño

| # | Decisión | Alternativa descartada | Motivo |
|---|----------|------------------------|--------|
| C1 | Claves sustitutas como hash `MD5` de la clave natural, con un macro común | `ROW_NUMBER()` | Determinista: la misma entidad tiene la misma clave en cualquier ejecución. `fct_ventas_linea` ya usa `MD5` para su propia clave |
| C2 | `fct_ventas_linea` incremental con `unique_key` y filtro por `_loaded_at`, sin `NOT EXISTS` | Mantener solo inserción, o pasar a `table` | Sigue siendo incremental como pide la rúbrica, y una fila que cambia en la fuente se reemplaza |
| C3 | Conversión tolerante con `pg_input_is_valid` de PostgreSQL 16, envuelta en un macro `convertir_seguro` | Expresiones regulares por tipo | La función usa el mismo analizador que el cast: detecta `2026-02-30`, meses `13` y desbordes de `NUMERIC(5,4)` sin reimplementar reglas |
| C4 | Claves primarias y foráneas físicas creadas con `post_hook` mediante macros idempotentes | Contratos de modelo de dbt | Los contratos obligan a declarar el tipo de cada columna de cada modelo; los `post_hook` resuelven claves sin tocar el resto |
| C5 | DDL de referencia de `marts` extraído con `pg_dump --schema-only` después de una ejecución | DDL escrito a mano | Refleja exactamente lo que existe; dbt sigue siendo el que crea los objetos |
| C6 | Ingresos = ventas `COMPLETADA` | Contar todas | Una venta anulada o pendiente no es ingreso |
| C7 | Casos de calidad cargados en un schema aparte, `raw_calidad`, y probados con una variable de dbt | Inyectarlos en `raw` | La corrida principal y sus cifras no se tocan (decisión D8) |
| C8 | pgAdmin con perfil de Compose `herramientas` | Quitarlo | B lo usa para explorar; con el perfil no arranca salvo que se pida |

## C1 — Claves sustitutas

Macro nuevo `macros/clave_sustituta.sql`:

```sql
{% macro clave_sustituta(columnas) -%}
    MD5({{ columnas | join(" || '|' || ") }}::TEXT)
{%- endmacro %}
```

| Modelo | Clave natural | Antes | Después |
|--------|---------------|-------|---------|
| `dim_cliente` | `id_cliente` | `ROW_NUMBER()` entero | `clave_sustituta(['id_cliente'])` |
| `dim_producto` | `id_producto` | `ROW_NUMBER()` | `clave_sustituta(['id_producto'])` |
| `dim_sucursal` | `id_sucursal` | `ROW_NUMBER()` | `clave_sustituta(['id_sucursal'])` |
| `dim_categoria` | `id_categoria` | `ROW_NUMBER()` | `clave_sustituta(['id_categoria'])` |
| `dim_marca` | `id_marca` | `ROW_NUMBER()` | `clave_sustituta(['id_marca'])` |
| `dim_promocion` | `id_promocion` | `ROW_NUMBER()` | `clave_sustituta(['id_promocion'])` |
| `dim_fecha` | fecha | `YYYYMMDD` entero | Sin cambio: ya es determinista |

Los hechos siguen uniéndose a las dimensiones por clave natural y toman la clave sustituta de la dimensión. Ningún hecho calcula el hash por su cuenta.

Las claves dejan de ser enteros: las consultas de `sql/validaciones/` que las usan se revisan, aunque en su mayoría unen por igualdad y no cambian.

## C2 — Hecho incremental

```sql
{{ config(
    materialized='incremental',
    unique_key='id_detalle',
    on_schema_change='sync_all_columns',
    post_hook=[...claves, ver C4...]
) }}
...
{% if is_incremental() %}
WHERE v._loaded_at > (SELECT COALESCE(MAX(_loaded_at), '1900-01-01') FROM {{ this }})
{% endif %}
```

- `int_ventas_linea` debe exponer `_loaded_at`; el hecho lo conserva como columna de control.
- Con `unique_key`, dbt reemplaza las filas existentes con la misma `id_detalle`.
- **Comportamiento honesto con este pipeline:** como la ingesta trunca y recarga `raw` en cada ejecución, todas las filas llegan con un `_loaded_at` nuevo y el incremental las reprocesa todas. El resultado es correcto; la ventaja de rendimiento aparecería con una ingesta incremental. El README lo explica.
- Una línea eliminada en la fuente no se elimina del hecho. Se documenta como limitación; la fuente no elimina líneas.
- Confirmar contra la documentación de dbt-postgres 1.11 la estrategia por defecto con `unique_key`.

## C3 — Conversión tolerante

Macro nuevo `macros/convertir_seguro.sql`:

```sql
{% macro convertir_seguro(columna, tipo) -%}
    CASE WHEN pg_input_is_valid(TRIM({{ columna }}), '{{ tipo }}')
         THEN TRIM({{ columna }})::{{ tipo }} END
{%- endmacro %}
```

- Reemplaza todas las conversiones de los 12 modelos de `staging` y la de `int_metas_ventas`.
- Mantiene las reglas de negocio que B ya aplicaba, por ejemplo precios no negativos, como condiciones aparte y explícitas.
- Antes de usarla, confirmar en la documentación de PostgreSQL 16 la firma de `pg_input_is_valid` y que acepta tipos con modificador, como `numeric(5,4)`.

## C4 — Claves físicas

Macros nuevos en `macros/restricciones.sql`:

| Macro | Qué hace |
|-------|----------|
| `clave_primaria(columna)` | `ALTER TABLE {{ this }} DROP CONSTRAINT IF EXISTS pk_<tabla>; ALTER TABLE {{ this }} ADD CONSTRAINT pk_<tabla> PRIMARY KEY (<columna>)` |
| `clave_foranea(columna, dimension, columna_dimension)` | Igual, con `fk_<tabla>_<columna>` y `REFERENCES` hacia la dimensión |

- Cada dimensión declara su `clave_primaria` en `post_hook`.
- Cada hecho declara su `clave_primaria` y una `clave_foranea` por cada dimensión que referencia.
- Los hechos se construyen después de sus dimensiones por las dependencias de `ref()`, así que las dimensiones ya tienen su clave primaria cuando se crea la foránea.
- Cuando dbt reconstruye una dimensión, su borrado en cascada elimina las foráneas que la referencian. Los hechos se ejecutan después y las vuelven a crear. Esto se verifica con dos ejecuciones seguidas (requisito R5.3).
- Para claves foráneas que admiten nulos (por ejemplo, una venta cuyo cliente no se encontró), la restricción permite `NULL`; la prueba `not_null` las reporta.

### DDL de referencia

`sql/ddl/03_marts_referencia.sql`, generado con:

```
pg_dump --schema-only --schema=marts --no-owner --no-privileges
```

Encabezado obligatorio: indica que es una referencia generada, la fecha, el comando y que dbt crea los objetos. No se ejecuta en la inicialización del DW: queda fuera de `/docker-entrypoint-initdb.d` porque crearía tablas que dbt espera crear.

Como `sql/ddl/` está montado como scripts de inicialización del DW, el archivo va en `sql/ddl/referencia/`, que el montaje no ejecuta. Confirmar que PostgreSQL no ejecuta subcarpetas de `/docker-entrypoint-initdb.d`.

## C5 — Pruebas

| Dónde | Prueba | Columnas |
|-------|--------|----------|
| `marts` | `unique`, `not_null` | Toda clave sustituta |
| `marts` | `relationships` | Toda clave foránea de los cinco hechos y de `dim_promocion` |
| `marts` | `accepted_values` | `canal`, `metodo_pago`, `estado`, `tipo_cliente`, `motivo`, `activo`, con los valores reales consultados en `raw` |
| `staging` | `not_null` | Columnas obligatorias según el contrato: claves, fechas de transacción, cantidades, precios, nombres |
| `staging` | `relationships` | `stg_oltp__venta_detalle.id_venta` hacia `stg_oltp__venta` |
| Singular | Ya existe | `assert_ventas_subtotal_consistente` se conserva |

`int_ventas_linea` pasa de `INNER JOIN` a `LEFT JOIN` con la venta, para que una línea huérfana llegue al hecho y la prueba de relación la reporte.

Los valores de `accepted_values` se obtienen consultando `raw`, no se suponen.

## C6 — Consultas y validaciones

| Archivo | Cambio |
|---------|--------|
| `sql/validaciones/02_ventas_por_sucursal.sql` | Filtra `estado = 'COMPLETADA'`; agrega columnas con conteo de anuladas y pendientes |
| `sql/validaciones/03_metas_vs_ventas.sql` | Filtra `estado = 'COMPLETADA'` |
| `sql/validaciones/dag/01_integridad_referencial_marts.sql` | Cubre los cinco hechos, incluidas sus claves de fecha |
| `sql/validaciones/dag/02_reglas_negocio_marts.sql` | Quita condiciones imposibles (negativos que `staging` ya dejó en `NULL`) y valida lo que sí puede ocurrir |

## C7 — Casos de calidad

- Script `sql/calidad/cargar_casos_calidad.sql` (o módulo Python, según resulte más simple) que crea `raw_calidad` como copia de `raw` y le aplica cada caso de `casos_calidad_opcionales.csv` que corresponda a una tabla existente.
- `_fuentes.yml` usa `schema: "{{ var('schema_raw', 'raw') }}"`, de modo que `dbt test --vars '{schema_raw: raw_calidad}'` prueba contra la copia.
- Los modelos de esa corrida se escriben en un objetivo o schema aparte para no tocar `staging` ni `marts`.
- Resultado esperado: cada caso aplicable produce al menos una prueba fallida. Se guarda como evidencia.
- La decisión D8 queda: los casos no se cargan en la corrida principal; se usan para demostrar las pruebas de calidad.

## C8 — pgAdmin

```yaml
pgadmin:
  image: dpage/pgadmin4:<versión fija>
  profiles: ["herramientas"]
  ports:
    - "${PGADMIN_PORT:-8081}:80"
  environment:
    PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL:?PGADMIN_EMAIL is required}
    PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD:?PGADMIN_PASSWORD is required}
  volumes:
    - pgadmin_data:/var/lib/pgadmin
```

- Se arranca con `docker compose --profile herramientas up -d pgadmin`.
- Las tres variables nuevas van a `.env.example` con valores de ejemplo no personales.
- La versión fija se confirma en el registro oficial de la imagen.
- Confirmar que la sintaxis `${VAR:?}` en un servicio con perfil inactivo no obliga a definir la variable para el arranque normal; si lo hace, usar valores por defecto no sensibles solo para esas variables y documentarlo.

## Documentos

| Documento | Cambio |
|-----------|--------|
| `Proyecto1/README.md` | Corregir afirmaciones falsas; explicar claves, incremental, restricciones, regla de ingresos y casos de calidad; cifras desde la evidencia nueva |
| `dbt_project/README.md` | Quitar secciones repetidas y afirmaciones incorrectas; documentar los macros nuevos |
| `models/marts/_marts.yml` | Descripción de cada modelo y columna |
| `docs/guia_rol_b.md` | Reflejar lo que B decidió e hizo y los cambios de esta feature |
| `.specs/steering/architecture.md` | Decisiones D12 y cierre de D8; estado final |
| `tests/dag/test_esqueleto_dbt.py` | La prueba de "un solo modelo" pasa a comprobar solo lo que el rol A garantiza: configuración, perfil, macro de schema y fuentes |

## Archivos de la feature

```
Proyecto1/
├── docker-compose.yml, .env.example                     pgAdmin
├── dbt_project/
│   ├── macros/clave_sustituta.sql                       nuevo
│   ├── macros/convertir_seguro.sql                      nuevo
│   ├── macros/restricciones.sql                         nuevo
│   ├── models/staging/*.sql, _staging.yml, _fuentes.yml
│   ├── models/intermediate/*.sql
│   ├── models/marts/*.sql, _marts.yml
│   └── README.md
├── sql/
│   ├── ddl/referencia/03_marts_referencia.sql           nuevo
│   ├── calidad/                                         nuevo
│   └── validaciones/*.sql, validaciones/dag/*.sql
├── tests/
│   ├── dag/test_esqueleto_dbt.py                        ajuste
│   └── cierre/                                          nuevo
├── evidencia/                                           regenerada
├── docs/guia_rol_b.md
└── README.md
```

## Estrategia de pruebas

```
Proyecto1/tests/cierre/
├── test_claves_estables.py       dos ejecuciones; cliente con id 0 agregado en la fuente
├── test_incremental.py           cambio de estado de una venta en la fuente
├── test_conversiones.py          valores inválidos en una copia de raw
├── test_restricciones.py         PK y FK presentes tras una y dos ejecuciones
├── test_consultas.py             ingresos solo de ventas completadas
├── test_casos_calidad.py         cada caso aplicable detectado
└── test_pgadmin.py               compose estático
```

- Las pruebas que modifican la base fuente restauran su estado al terminar y verifican los conteos del contrato.
- Ninguna prueba escribe en `staging` ni `marts` salvo a través de una ejecución normal del pipeline.
- Toda ejecución de `psql` usa `ON_ERROR_STOP=1`.

## Evidencia

Se regenera desde una ejecución del DAG en un entorno limpio:

| Archivo | Contenido |
|---------|-----------|
| `dag_estados_tareas.txt` | Estado de las 17 tareas |
| `dag_log_dbt_run.txt`, `dag_log_dbt_test.txt` | Registros reales del DAG, reemplazando los generados a mano |
| `marts_conteos.txt` | Filas por tabla de `marts` |
| `marts_restricciones.txt` | Claves primarias y foráneas del schema `marts` |
| `casos_calidad_resultado.txt` | Pruebas que fallan con cada caso de calidad |
| `validacion_*.txt` | Resultado de las consultas analíticas con la regla de ingresos |

Las capturas existentes se conservan. Si cambia el número de tareas o su resultado, se pide al integrante una captura nueva.

## Puntos abiertos

Resueltos en T1 el 2026-10-14. Cada respuesta indica su fuente y la comprobación empírica.

- [x] **`pg_input_is_valid` en PostgreSQL 16.** Firma `pg_input_is_valid(text, text)`, devuelve `boolean`; el segundo argumento es el nombre del tipo y admite modificadores. Fuente: consulta a `pg_proc` en el contenedor `dw` (PostgreSQL 16.15). Comprobado: `('2026-02-30','date')` da `f`; `('13','smallint')` da `t`; `('12.5','numeric(5,4)')` da `f`; `('0.1234','numeric(5,4)')` da `t`; `('123456789012','integer')` da `f` y con `bigint` da `t`; `('12.5','integer')` da `f`. Con entrada `NULL` devuelve `NULL`, que el `CASE` trata como no válido y deja `NULL`.
- [x] **Estrategia incremental con `unique_key`.** `delete+insert`. Fuente: documentación de dbt para Postgres (`postgres-configs`, estrategias: `append` por defecto sin `unique_key`, `delete+insert` por defecto con `unique_key`) y macro instalada `postgres__get_incremental_default_sql` en `dbt/include/postgres/macros/materializations/incremental_strategies.sql` (dbt-postgres 1.11.0): si hay `unique_key` llama a `get_incremental_delete_insert_sql`. No hace falta declarar `incremental_strategy`.
- [x] **Subcarpetas de `/docker-entrypoint-initdb.d`.** No se ejecutan. Fuente: el script `/usr/local/bin/docker-entrypoint.sh` de la imagen `postgres:16` recorre los elementos del directorio sin recursión y solo ejecuta `*.sql`, `*.sql.gz` y `*.sh`; cualquier otra entrada, incluida una carpeta, cae en la rama `ignoring`. La documentación oficial de la imagen solo describe esos tipos. Se vuelve a comprobar en T11 con un reinicio limpio.
- [x] **Versión fija de `dpage/pgadmin4`.** `9.18.0` (publicada el 2026-09-17, etiqueta inmutable de versión menor y parche; existen también `9.18` y `latest`, descartadas). Fuente: API de Docker Hub, listado de etiquetas de `dpage/pgadmin4`.
- [x] **`${VAR:?}` con perfil inactivo.** Sí obliga a definir la variable: Compose interpola todos los servicios aunque su perfil esté inactivo. Comprobado con un archivo de prueba y `docker compose config` sin la variable: falla con `required variable PGADMIN_PASSWORD is missing a value`, con y sin `--profile`. **Cambio sobre C8:** `PGADMIN_EMAIL` y `PGADMIN_PASSWORD` usan `${VAR:-valor}`; el correo por defecto es `pgadmin@example.com` (no personal) y la contraseña por defecto es vacía, de modo que no hay credencial literal y pgAdmin, que exige una contraseña, no arranca sin definirla. Se documenta en `.env.example` y el README.
- [x] **Valores reales de las columnas categóricas** (consulta a `raw`): `canal` = Mayorista, Televenta, Tienda, Web; `metodo_pago` = Crédito, Efectivo, Tarjeta, Transferencia; `estado` = ANULADA, COMPLETADA, PENDIENTE; `tipo_cliente` = Mayorista, Minorista, Restaurante, Tienda de barrio; `motivo` (devoluciones) = Cliente desistió, Empaque defectuoso, Error de despacho, Producto dañado, Vencimiento cercano; `activo` = `true` en las 80 filas de `producto`.
