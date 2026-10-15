# Tareas — `ajustes-cierre`

Doce tareas ordenadas con TDD. Las primeras corrigen el modelo de datos, después las pruebas y restricciones, y al final la documentación y la evidencia. **Ninguna se ejecuta hasta aprobar este documento.**

- **Requisitos:** [requirements.md](requirements.md)
- **Diseño:** [design.md](design.md)
- **Ejecuta:** rol A, con autorización de B para su zona (decisión D12)

Las rutas son relativas a `Proyecto1/` y los comandos se ejecutan desde esa carpeta. Los campos Rojo, Verde, Verificación y Commit significan lo mismo que en las features anteriores.

## Resumen

| # | Tarea | Hallazgos | Depende de |
|---|-------|-----------|-----------|
| T0 | Rama y decisiones | — | — |
| T1 | Verificaciones previas | — | T0 |
| T2 | Prueba obsoleta del rol A | H11 | T0 |
| T3 | Conversiones tolerantes | H3 | T1 |
| T4 | Claves sustitutas estables | H1 | T3 |
| T5 | Hecho incremental correcto | H1 | T4 |
| T6 | Cobertura de pruebas dbt | H4, H5 | T5 |
| T7 | Claves físicas y DDL de referencia | H6 | T6 |
| T8 | Consultas y validaciones finales | H2, H9 | T7 |
| T9 | Casos de calidad | H13 | T6 |
| T10 | pgAdmin | H10 | T0 |
| T11 | Arranque limpio y evidencia | H14 | T1 a T10 |
| T12 | Documentación y aviso a B | H7, H8, H12 | T11 |

## T0 — Rama y decisiones

- [x] Crear la rama `fix/ajustes-cierre` desde `main` actualizado.
- [x] Registrar en [architecture.md](../../steering/architecture.md) la decisión D12: desde el 2026-10-14, B autoriza que A edite `dbt_project/` y `sql/validaciones/`, informándole los cambios.
- [x] Registrar el cierre de D8 según la decisión C7 de [design.md](design.md).

**Verificación:** `git branch --show-current` devuelve `fix/ajustes-cierre`.
**Commit:** `docs(p1): record closing decisions for role b fixes`

## T1 — Verificaciones previas

Sin código. Cada respuesta se anota en "Puntos abiertos" de [design.md](design.md) con su fuente.

- [x] Firma de `pg_input_is_valid` en PostgreSQL 16 y si acepta `numeric(5,4)`; comprobarlo además con una consulta en el contenedor `dw`.
- [x] Estrategia incremental por defecto de dbt-postgres 1.11 cuando hay `unique_key`.
- [x] Si `/docker-entrypoint-initdb.d` ejecuta subcarpetas.
- [x] Versión fija de `dpage/pgadmin4` y comportamiento de `${VAR:?}` en un servicio con perfil inactivo.
- [x] Valores reales de `canal`, `metodo_pago`, `estado`, `tipo_cliente`, `motivo` y `activo`, consultados en `raw`.

**Verificación:** los cinco puntos quedan marcados con su respuesta.
**Commit:** `docs(p1): confirm postgres, dbt and pgadmin details for closing fixes`

## T2 — Prueba obsoleta del rol A

- [x] **Rojo:** confirmar que `test_models_contiene_unico_archivo_sql` falla con el proyecto actual.
- [x] **Verde:** reemplazarla por pruebas de lo que el rol A garantiza: existen `dbt_project.yml`, `profiles.yml` sin credenciales literales, el macro de schema y las fuentes de las 12 tablas.
- [x] Confirmar que ninguna otra prueba del rol A depende del contenido de los modelos.

**Verificación:** `pytest tests/dag -k "esqueleto"`.
**Commit:** `test(p1-dag): stop asserting skeleton-only dbt models`

## T3 — Conversiones tolerantes

- [x] **Rojo (integración):** `tests/cierre/test_conversiones.py` crea una copia de `raw` con `2026-02-30` en una fecha, `13` en un mes de `metas_ventas`, `12.5` en un descuento y un entero de 12 dígitos; ejecuta `dbt run` contra la copia y exige que termine con código 0, que esos valores queden en `NULL` y que `dbt test` reporte las columnas obligatorias afectadas. Falla hoy porque `dbt run` se detiene.
- [x] **Verde:** crear `macros/convertir_seguro.sql` y usarlo en todos los modelos de `staging` y en `int_metas_ventas`.
- [x] Conservar como condiciones explícitas las reglas de negocio que B ya aplicaba.
- [x] Ejecutar el pipeline normal y comprobar que los conteos de `marts` no cambian.

**Verificación:** `pytest tests/cierre -k "conversiones"` y una ejecución del DAG en verde.
**Commit:** `fix(p1-dbt): convert staging types tolerantly with pg_input_is_valid`

## T4 — Claves sustitutas estables

- [ ] **Rojo (integración):** `tests/cierre/test_claves_estables.py`:
  - Dos ejecuciones seguidas dejan las mismas claves en cada dimensión.
  - Tras agregar en la base fuente un cliente con identificador 0 y ejecutar de nuevo, la clave de cada uno de los 250 clientes existentes no cambia y cada línea de `fct_ventas_linea` apunta al mismo cliente.
  - La prueba elimina el cliente 0 y vuelve a ejecutar al terminar.
- [ ] **Verde:** crear `macros/clave_sustituta.sql` y usarlo en las seis dimensiones con `ROW_NUMBER()`.
- [ ] Revisar las consultas de `sql/validaciones/` que usan claves.

**Verificación:** `pytest tests/cierre -k "claves_estables"`.
**Commit:** `fix(p1-dbt): derive dimension surrogate keys from natural keys`

## T5 — Hecho incremental correcto

- [ ] **Rojo (integración):** `tests/cierre/test_incremental.py`: tras una ejecución completa, cambiar en la base fuente una venta `PENDIENTE` a `ANULADA`, ejecutar de nuevo y exigir que sus líneas en `fct_ventas_linea` tengan `ANULADA` y que el hecho conserve 3209 filas. Restaurar el estado al terminar.
- [ ] **Verde:** exponer `_loaded_at` en `int_ventas_linea` y cambiar el filtro incremental según C2 de [design.md](design.md).
- [ ] Confirmar que `fct_ventas_linea` sigue materializado como `incremental`.

**Verificación:** `pytest tests/cierre -k "incremental"`.
**Commit:** `fix(p1-dbt): let the incremental sales fact update changed rows`

## T6 — Cobertura de pruebas dbt

- [ ] **Rojo:** prueba estática que lee los YAML y exige: `unique` y `not_null` en cada clave sustituta de `marts`; `relationships` en cada clave foránea de los cinco hechos y de `dim_promocion`; `accepted_values` en las columnas categóricas de T1; `relationships` de `stg_oltp__venta_detalle.id_venta` hacia `stg_oltp__venta`.
- [ ] **Rojo (integración):** una línea de detalle con una venta inexistente, en una copia de `raw`, llega al hecho y hace fallar `dbt test`.
- [ ] **Verde:** agregar las pruebas y cambiar `int_ventas_linea` a `LEFT JOIN`.
- [ ] Agregar `not_null` a las columnas obligatorias de `staging` según el contrato.
- [ ] Ejecutar `dbt test` sobre los datos reales: todas las pruebas pasan.

**Verificación:** `pytest tests/cierre -k "cobertura"` y `dbt test` en verde.
**Commit:** `test(p1-dbt): cover keys, relationships and categorical values`

## T7 — Claves físicas y DDL de referencia

- [ ] **Rojo (integración):** `tests/cierre/test_restricciones.py`: tras una ejecución, cada tabla de `marts` tiene clave primaria y cada clave foránea de cada hecho existe como restricción; tras una segunda ejecución siguen existiendo.
- [ ] **Verde:** crear `macros/restricciones.sql` y declarar los `post_hook` en dimensiones y hechos.
- [ ] Generar `sql/ddl/referencia/03_marts_referencia.sql` con `pg_dump --schema-only`, con el encabezado de [design.md](design.md).
- [ ] Confirmar que un reinicio limpio no ejecuta ese archivo.

**Verificación:** `pytest tests/cierre -k "restricciones"` y dos ejecuciones del DAG en verde.
**Commit:** `feat(p1-dbt): add physical keys to marts and reference ddl`

## T8 — Consultas y validaciones finales

- [ ] **Rojo (integración):** `tests/cierre/test_consultas.py`: el total de ingresos de `02_ventas_por_sucursal.sql` coincide con la suma de subtotales de ventas `COMPLETADA`; `03_metas_vs_ventas.sql` usa el mismo criterio.
- [ ] **Rojo (integración):** cada validación de `sql/validaciones/dag/` detecta un caso inválido preparado para ella en una copia de `marts`.
- [ ] **Verde:** aplicar los cambios de C6 de [design.md](design.md).
- [ ] Ejecutar el DAG: `validar_marts` en verde.

**Verificación:** `pytest tests/cierre -k "consultas"`.
**Commit:** `fix(p1-sql): count only completed sales and cover all facts in validations`

## T9 — Casos de calidad

- [ ] **Rojo (integración):** `tests/cierre/test_casos_calidad.py`: tras cargar los casos en `raw_calidad` y ejecutar dbt contra esa copia, cada caso aplicable a una tabla de `raw` produce al menos una prueba fallida; `staging` y `marts` de la corrida principal no cambian.
- [ ] **Verde:** implementar la carga de C7 y la variable `schema_raw` en `_fuentes.yml`.
- [ ] Listar los casos que no aplican a ninguna tabla cargada y explicar por qué.
- [ ] Eliminar `raw_calidad` y los objetos de prueba al terminar.

**Verificación:** `pytest tests/cierre -k "casos_calidad"`.
**Commit:** `feat(p1-dbt): demonstrate quality tests against optional quality cases`

## T10 — pgAdmin

- [ ] **Rojo (estática):** `tests/cierre/test_pgadmin.py` y la prueba existente de imágenes: ninguna imagen sin versión fija; pgAdmin tiene perfil `herramientas`; sus credenciales y su puerto salen de variables; un único volumen montado en `/var/lib/pgadmin`; `.env.example` contiene las variables nuevas con valores no personales.
- [ ] **Rojo (integración):** `docker compose up -d` no inicia pgAdmin.
- [ ] **Verde:** aplicar C8 de [design.md](design.md).
- [ ] Iniciar pgAdmin con el perfil y comprobar que responde en su puerto.

**Verificación:** `pytest tests/cierre -k "pgadmin"` y `pytest tests/entorno`.
**Commit:** `fix(p1-entorno): pin pgadmin and read its settings from env`

## T11 — Arranque limpio y evidencia

- [ ] `docker compose down -v` y `docker compose up -d`.
- [ ] Ejecutar el DAG y esperar el resultado: las 17 tareas en `success`.
- [ ] Ejecutar la suite completa: `pytest tests/entorno tests/contrato tests/ingesta tests/dag tests/cierre`, y la prueba lenta de forma explícita.
- [ ] Regenerar en `evidencia/` los archivos de [design.md](design.md) desde esa ejecución, como `.txt`.
- [ ] Quitar los archivos de evidencia generados a mano que queden reemplazados.
- [ ] Revisar que ningún archivo de evidencia contenga credenciales.

**Verificación:** suite completa en verde en un entorno limpio; evidencia versionada.
**Commit:** `docs(p1): regenerate evidence from a clean dag run`

## T12 — Documentación y aviso a B

- [ ] `_marts.yml`: descripción de cada modelo y cada columna.
- [ ] `README.md`: corregir las afirmaciones señaladas en la revisión; explicar claves, incremental, restricciones, regla de ingresos y casos de calidad; cada cifra tomada de la evidencia nueva.
- [ ] `dbt_project/README.md`: quitar las secciones repetidas y la afirmación incorrecta sobre selección de modelos; documentar los macros nuevos.
- [ ] `docs/guia_rol_b.md` y [architecture.md](../../steering/architecture.md): estado final y decisiones.
- [ ] Indicar si hace falta una captura nueva de Airflow.
- [ ] Redactar `docs/cambios_ajustes_cierre.md` para B: cada cambio, su motivo y el archivo afectado.
- [ ] Ejecutar `dbt docs generate` sin errores.

**Verificación:** ninguna afirmación del README contradice el código o la evidencia; revisión manual contra la lista de hallazgos.
**Commit:** `docs(p1): align documentation with closing fixes`

## Definición de terminado

- [ ] Los catorce hallazgos de [requirements.md](requirements.md) están resueltos o tienen una explicación registrada.
- [ ] Todos los escenarios Gherkin pasan.
- [ ] La suite completa pasa en un entorno limpio.
- [ ] El DAG corre en verde dos veces seguidas con las restricciones físicas activas.
- [ ] B tiene el resumen de cambios.
- [ ] Pull request de `fix/ajustes-cierre` hacia `main` listo para abrir.
