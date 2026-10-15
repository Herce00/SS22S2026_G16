# Cambios de los ajustes de cierre

Resumen para el Rol B de lo que el Rol A cambió en `dbt_project/` y `sql/validaciones/` con su autorización del 2026-10-14 (decisión D12 de [architecture.md](../../.specs/steering/architecture.md)). Los cambios salen de la revisión del commit `5c50f47` (`feat: add parte b`) y están en la rama `fix/ajustes-cierre`. El modelo dimensional no cambió: son los mismos hechos, dimensiones y granos.

Especificación completa: [requirements](../../.specs/features/ajustes-cierre/requirements.md), [design](../../.specs/features/ajustes-cierre/design.md) y [tasks](../../.specs/features/ajustes-cierre/tasks.md).

## Qué cambió y por qué

| Hallazgo | Cambio | Motivo | Archivos |
|----------|--------|--------|----------|
| H1 | Las claves sustitutas de las seis dimensiones pasan de `ROW_NUMBER()` a `MD5` de la clave natural, con el macro `clave_sustituta` | Con `ROW_NUMBER()` agregar un cliente con identificador menor desplazaba la clave de todos los demás, y las filas ya cargadas del hecho incremental quedaban apuntando a otro cliente. Ahora la misma entidad tiene siempre la misma clave | `macros/clave_sustituta.sql`, `models/marts/dim_*.sql` |
| H1 | `fct_ventas_linea` sigue siendo incremental pero filtra por `_loaded_at` en lugar de `NOT EXISTS`; `int_ventas_linea` expone `_loaded_at` | Con `NOT EXISTS` una venta que cambiaba en la fuente (por ejemplo `PENDIENTE` a `ANULADA`) nunca se actualizaba. Con `unique_key` dbt reemplaza la fila | `models/marts/fct_ventas_linea.sql`, `models/intermediate/int_ventas_linea.sql` |
| H3 | Todas las conversiones de tipo usan el macro `convertir_seguro` (`pg_input_is_valid`) | Una fecha imposible como `2026-02-30`, un mes `13` o un decimal fuera de `NUMERIC(5,4)` pasaban la expresión regular y detenían `dbt run`. Ahora quedan en `NULL` y la prueba `not_null` los reporta. Se conservaron como condiciones explícitas el formato ISO de las fechas y la exclusión de negativos | `macros/convertir_seguro.sql`, `models/staging/*.sql`, `models/intermediate/int_metas_ventas.sql` |
| H4 | Pruebas nuevas: `relationships` en todas las claves foráneas de los hechos y de `dim_promocion`, `accepted_values` en las columnas categóricas de `marts`, `not_null` en las columnas obligatorias del contrato, y cinco pruebas singulares de reglas de negocio | Faltaban relaciones, valores aceptados y nulos. Los valores de `accepted_values` se consultaron en `raw` | `models/marts/_marts.yml`, `models/staging/_staging.yml`, `tests/*.sql` |
| H4 | Los argumentos de las pruebas pasan a la propiedad `arguments:` | Es la sintaxis vigente de dbt 1.12; quita las 17 advertencias de deprecación | `_marts.yml`, `_staging.yml` |
| H5 | `int_ventas_linea` usa `LEFT JOIN` con la venta | El `INNER JOIN` descartaba en silencio las líneas sin venta. Ahora llegan al hecho y la prueba `relationships` de `stg_oltp__venta_detalle.id_venta` las reporta | `models/intermediate/int_ventas_linea.sql` |
| H6 | Claves primarias y foráneas físicas en `marts`, creadas con `post_hook` (`clave_primaria`, `clave_foranea`); DDL de referencia extraído con `pg_dump` | El enunciado pide hechos, dimensiones, relaciones y claves. El DDL es solo documentación y no se ejecuta al iniciar el DW | `macros/restricciones.sql`, `models/marts/*.sql`, `sql/ddl/referencia/` |
| H2 | Las consultas de ingresos cuentan solo ventas `COMPLETADA`; `02_ventas_por_sucursal.sql` muestra aparte las anuladas y las pendientes | Una venta anulada o pendiente no es ingreso | `sql/validaciones/02_ventas_por_sucursal.sql`, `03_metas_vs_ventas.sql` |
| H9 | `dag/01` cubre los cinco hechos con todas sus claves, `dag/02` valida solo lo que puede ocurrir (nulos, cantidades en cero, descuentos fuera de rango) y `01_conteos_marts.sql` cubre las 12 tablas | Antes había condiciones imposibles (negativos que `staging` ya deja en `NULL`) y faltaban hechos | `sql/validaciones/**` |
| H7 | Descripción de cada modelo y cada columna de `marts` | El estándar lo exige y `dbt docs` debe mostrarlas | `models/marts/_marts.yml` |
| H8 | README y `dbt_project/README.md` corregidos | Contenían afirmaciones falsas o desactualizadas | `README.md`, `dbt_project/README.md` |
| H13 | Los casos de calidad opcionales se cargan en una copia de `raw` (`raw_calidad`) y se prueban con la variable `schema_raw` | Demuestran las pruebas sin alterar las cifras de la corrida principal (D8) | `sql/calidad/cargar_casos_calidad.py`, `models/staging/_fuentes.yml`, `macros/generate_schema_name.sql` |
| H14 | La evidencia de dbt se regeneró desde una ejecución del DAG en un entorno limpio | La anterior se había generado a mano | `evidencia/` |
| H10 | pgAdmin con versión fija, perfil `herramientas` y credenciales desde `.env`; un solo volumen | La imagen no tenía versión, la contraseña y el correo eran literales y los volúmenes estaban mal montados | `docker-compose.yml`, `.env.example` |
| H11, H12 | Pruebas del Rol A que no dependen del contenido de los modelos; guía y steering actualizados | Una prueba exigía que el proyecto tuviera un solo modelo | `tests/dag/test_esqueleto_dbt.py`, `docs/guia_rol_b.md` |

## Qué debe hacer B al retomar el proyecto

1. Si ya tiene `marts` creado en su entorno, ejecute una vez `dbt run --full-refresh`: las claves de las dimensiones cambiaron de entero a texto y el hecho incremental conserva las columnas anteriores. Un `docker compose down -v` seguido de `docker compose up -d` también lo resuelve.
2. pgAdmin ya no arranca con `docker compose up`. Defina `PGADMIN_PASSWORD` en su `.env` (hay un ejemplo en `.env.example`) y use `docker compose --profile herramientas up -d pgadmin`.
3. Los ingresos que muestre en el informe son los de ventas `COMPLETADA`. La regla está en `sql/validaciones/02_ventas_por_sucursal.sql`.
4. Las claves de los hechos y las dimensiones son texto (`MD5`), salvo `dim_fecha.fecha_key` y `fct_devoluciones.devolucion_key`. Cualquier consulta nueva debe unirse por igualdad, no por rango.
5. Al agregar un modelo en `marts`, use `clave_sustituta` para su clave y declare sus restricciones con `clave_primaria` y `clave_foranea` en el `post_hook`.

## Qué no cambió

- El diseño dimensional: hechos, dimensiones y granos.
- La ingesta, el contrato `raw` y el DAG (17 tareas).
- Las versiones fijadas: Airflow 3.3.2, Python 3.12, PostgreSQL 16, dbt-core 1.12.5 y dbt-postgres 1.11.0.
