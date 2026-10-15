# Proyecto dbt SG-Food

Proyecto dbt del pipeline ELT de SG-Food. El Rol A dejó el esqueleto (conexión, macro de schemas y fuentes) y el Rol B construyó sobre él las tres capas de modelos. Los ajustes de cierre posteriores (claves estables, conversiones tolerantes, restricciones físicas y pruebas) están descritos en [docs/cambios_ajustes_cierre.md](../docs/cambios_ajustes_cierre.md).

## Estructura

```text
dbt_project/
├── dbt_project.yml              # Nombre, perfil, rutas y materialización por carpeta
├── profiles.yml                 # Conexión a PostgreSQL con las variables DW_* (sin credenciales literales)
├── macros/
│   ├── generate_schema_name.sql # Escribe directamente en staging y marts; admite el prefijo de schema de pruebas
│   ├── convertir_seguro.sql     # Conversión de TEXT a otro tipo que devuelve NULL ante un valor inválido
│   ├── clave_sustituta.sql      # Clave sustituta determinista (MD5 de la clave natural)
│   └── restricciones.sql        # Claves primarias y foráneas físicas de marts (post_hook)
├── models/
│   ├── staging/                 # 12 vistas, una por tabla de raw (_fuentes.yml, _staging.yml)
│   ├── intermediate/            # 5 vistas con joins y lógica reutilizable (_intermediate.yml)
│   └── marts/                   # 7 dimensiones y 5 hechos (_marts.yml)
└── tests/                       # Pruebas singulares (reglas de negocio)
```

Los modelos `intermediate` se crean en el schema `staging` (`+schema: staging` en `dbt_project.yml`).

## Materialización

| Capa | Materialización | Schema | Modelos |
|------|-----------------|--------|---------|
| `staging` | Vista | `staging` | 12 |
| `intermediate` | Vista | `staging` | 5 |
| `marts` | Tabla | `marts` | 7 dimensiones y 4 hechos |
| `marts` | Incremental | `marts` | `fct_ventas_linea` |

## Macros

| Macro | Qué hace | Dónde se usa |
|-------|----------|--------------|
| `convertir_seguro(columna, tipo)` | Convierte `TEXT` con `pg_input_is_valid` de PostgreSQL 16, el mismo analizador del cast. Un valor inválido (`2026-02-30`, mes `13`, un decimal fuera de `NUMERIC(5,4)`, un entero que desborda) queda en `NULL` y `dbt run` no se detiene. Mantiene dos reglas de negocio como condiciones explícitas: las fechas deben tener formato ISO y los números no pueden ser negativos | Los 12 modelos de `staging` y `int_metas_ventas` |
| `clave_sustituta(columnas)` | `MD5` de la clave natural. La misma entidad recibe la misma clave en cualquier ejecución, sin importar el orden ni cuántas filas existan. Una clave natural nula se trata como texto vacío para que la clave nunca sea `NULL`; la prueba `not_null` de la clave natural reporta el problema | Las seis dimensiones y la clave de `fct_ventas_linea` |
| `clave_primaria(columna)`, `clave_foranea(columna, dimension, columna_dimension)` | Crean las restricciones físicas con `post_hook`, de forma idempotente: eliminan la restricción si existe y la vuelven a crear | Los 12 modelos de `marts` |
| `generate_schema_name` | Usa el schema personalizado tal cual. Con la variable `prefijo_schema` escribe en schemas paralelos (por ejemplo `cierre_staging`) | Todos los modelos |

## Claves y restricciones

- Las claves sustitutas `*_key` son texto (`MD5`), excepto `dim_fecha.fecha_key` (entero `AAAAMMDD`) y `fct_devoluciones.devolucion_key` (el identificador de la devolución). Los hechos se unen a las dimensiones por clave natural y toman la clave sustituta de la dimensión.
- Cada tabla de `marts` tiene clave primaria física, y cada clave foránea de los hechos (y las de `dim_producto` y `dim_promocion`) existe como restricción. dbt reconstruye una dimensión con `DROP ... CASCADE`, que elimina las claves foráneas que la referencian; los hechos se construyen después y las vuelven a crear. Por eso el pipeline se puede ejecutar varias veces seguidas.
- Las claves foráneas admiten `NULL`. Una venta cuyo cliente no se encontró queda con `cliente_key` nulo, y la prueba `not_null` de `fct_ventas_linea` lo reporta.
- Si cambia el tipo de una clave en un entorno que ya tiene `marts`, ejecute una vez `dbt run --full-refresh`: el hecho incremental conserva las columnas de la ejecución anterior.
- El DDL del schema, extraído de la base después de una ejecución real, está en [sql/ddl/referencia/03_marts_referencia.sql](../sql/ddl/referencia/03_marts_referencia.sql). Es solo documentación: dbt crea las tablas y el archivo no se ejecuta al iniciar el DW.

## Hecho incremental

`fct_ventas_linea` es `incremental` con `unique_key='id_detalle'`. En dbt-postgres 1.11 una clave única usa la estrategia `delete+insert`: la fila con el mismo `id_detalle` se reemplaza. El filtro compara `_loaded_at` con el máximo ya cargado, así que un cambio en la fuente (por ejemplo una venta que pasa de `PENDIENTE` a `ANULADA`) llega al hecho.

La ingesta trunca y recarga `raw` en cada ejecución, de modo que todas las filas llegan con un `_loaded_at` nuevo y el incremental las vuelve a procesar todas. El resultado es correcto; la ventaja de rendimiento aparecería con una ingesta incremental. Una línea eliminada en la fuente no se elimina del hecho; la fuente no elimina líneas.

## Pruebas

| Dónde | Pruebas |
|-------|---------|
| `marts` | `unique` y `not_null` en toda clave sustituta; `relationships` en toda clave foránea de los hechos y de `dim_promocion`; `accepted_values` en `canal`, `metodo_pago`, `estado`, `tipo_cliente`, `motivo` y `activo` |
| `staging` | `not_null` en toda columna obligatoria del contrato raw; `relationships` de `venta_detalle.id_venta` hacia `venta`, y de `venta.id_cliente` y `venta.id_sucursal` hacia sus tablas |
| Singulares (`tests/`) | `assert_ventas_subtotal_consistente`, `assert_ventas_cantidad_positiva`, `assert_ventas_descuento_en_rango`, `assert_inventario_vencimiento_posterior_al_corte`, `assert_metas_positivas`, `assert_devolucion_no_supera_venta` |

`int_ventas_linea` usa `LEFT JOIN` con la venta: una línea sin venta no se descarta, llega al hecho y la prueba de relación de `staging` la reporta.

### Casos de calidad opcionales

Los 10 casos de `data/casos_calidad_opcionales.csv` no se cargan en la corrida principal. El script [sql/calidad/cargar_casos_calidad.py](../sql/calidad/cargar_casos_calidad.py) crea el schema `raw_calidad` como copia de `raw` y aplica cada caso a una fila distinta. Después se prueba contra esa copia sin tocar `staging` ni `marts`:

```bash
docker compose exec -T airflow-scheduler python /opt/airflow/sql/calidad/cargar_casos_calidad.py
docker compose exec -T airflow-scheduler /opt/dbt-venv/bin/dbt run  --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project --vars '{schema_raw: raw_calidad, prefijo_schema: cierre_}'
docker compose exec -T airflow-scheduler /opt/dbt-venv/bin/dbt test --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project --vars '{schema_raw: raw_calidad, prefijo_schema: cierre_}'
docker compose exec -T airflow-scheduler python /opt/airflow/sql/calidad/cargar_casos_calidad.py --limpiar
```

`_fuentes.yml` usa `schema: "{{ var('schema_raw', 'raw') }}"`, y `prefijo_schema` envía los modelos a `cierre_staging` y `cierre_marts`. Cada uno de los 10 casos hace fallar al menos una prueba (ver `evidencia/casos_calidad_resultado.txt`).

## Cómo ejecutar dbt

Desde `Proyecto1/`, dentro del contenedor del scheduler (recomendado):

```bash
docker compose exec -T airflow-scheduler /opt/dbt-venv/bin/dbt debug --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
docker compose exec -T airflow-scheduler /opt/dbt-venv/bin/dbt run   --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
docker compose exec -T airflow-scheduler /opt/dbt-venv/bin/dbt test  --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
```

Para ejecutar solo una capa, use el selector `path:models/staging`, `path:models/intermediate` o `path:models/marts`. Un selector `path:` ejecuta únicamente los modelos de esa carpeta: no incluye sus dependencias. Para incluirlas anteponga `+` (`--select +path:models/marts`) o ejecute el proyecto completo, que es lo que hace el DAG.

Para generar la documentación navegable:

```bash
docker compose exec -T airflow-scheduler /opt/dbt-venv/bin/dbt docs generate --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
```

Las descripciones de cada modelo y columna están en [_staging.yml](models/staging/_staging.yml), [_intermediate.yml](models/intermediate/_intermediate.yml) y [_marts.yml](models/marts/_marts.yml).
