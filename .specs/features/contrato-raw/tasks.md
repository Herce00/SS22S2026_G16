# Tareas — `contrato-raw`

Ocho tareas ordenadas para dejar el contrato raw definido, verificado y materializado. Cada una indica la prueba que se escribe primero, la implementación mínima y cómo se verifica. **Ninguna se ejecuta hasta aprobar este documento.**

- **Requisitos:** [requirements.md](requirements.md)
- **Diseño:** [design.md](design.md)
- **Rol dueño:** A

Las rutas son relativas a `Proyecto1/` y los comandos se ejecutan desde esa carpeta. Los campos Rojo, Verde, Verificación y Commit significan lo mismo que en [entorno-base](../entorno-base/tasks.md).

## Resumen

| # | Tarea | Requisitos | Depende de | Zona |
|---|-------|-----------|-----------|------|
| T0 | Acuerdos con B | — | — | Amarilla |
| T1 | Versionar los datos oficiales | R1 | T0 | Verde |
| T2 | Configuración de fuentes | R3 | T1 | Amarilla |
| T3 | Base fuente poblada | R2, R3.4 | T2 | Verde |
| T4 | Tablas de `raw` | R4 | T2 | Amarilla |
| T5 | Documento de contrato | R5, R6 | T2 | Amarilla |
| T6 | Arranque desde cero | R2.1, R4.1, R6 | T3, T4, T5 | Verde |
| T7 | Documentación | — | T6 | Verde |

## T0 — Acuerdos con B

**Completada el 2026-10-09.** La pareja discutió y aceptó sin cambios los seis puntos de "Dependencias con el rol B" de [requirements.md](requirements.md). La implementación empieza en T1.

- [x] Validar con B los seis puntos de "Dependencias con el rol B".
- [x] Registrar cualquier cambio acordado en [design.md](design.md): no hubo cambios.
- [x] Confirmar que la rama activa es `feat/ingesta-airflow` (se comprueba al iniciar T1).

## T1 — Versionar los datos oficiales

- [x] **Rojo:** `tests/contrato/test_datos_oficiales.py` exige:
  - Existen en `data/` los ocho archivos oficiales.
  - Cada CSV empieza con BOM de UTF-8 y usa fin de línea CRLF.
  - Cada CSV tiene la cantidad de filas de datos indicada en [design.md](design.md).
  - `git check-attr text` reporta `unset` para los archivos de `data/`.
- [x] **Verde:** crear `.gitattributes` con `data/* -text` y agregar los archivos de `data/` al control de versiones.
- [x] Confirmar con `git diff --cached --stat` que no se modificó el contenido de ningún archivo.

**Verificación:** `pytest tests/contrato -k "datos_oficiales"`.
**Commit:** `feat(p1-contrato): track official source data`

## T2 — Configuración de fuentes

- [x] **Rojo:** `tests/contrato/test_fuentes_config.py` exige:
  - `python/config/fuentes.yml` existe, es YAML válido y declara `version: 1`.
  - Declara exactamente 12 fuentes: 7 de tipo `postgres` y 5 de tipo `csv`.
  - `tabla_raw` es único y está en `snake_case`.
  - Cada `origen` de tipo `csv` existe en `data/`; cada `origen` de tipo `postgres` tiene la forma `oltp_sgfood.<tabla>`.
  - Las columnas de cada fuente `csv` coinciden en nombre y orden con el encabezado leído como `utf-8-sig`.
  - Ninguna lista de columnas tiene duplicados ni incluye `_loaded_at` o `_source`.
  - `casos_calidad_opcionales.csv` no aparece.
  - El archivo no contiene contraseñas, hosts ni rutas absolutas.
- [x] **Verde:** crear `python/config/fuentes.yml` según las tablas de [design.md](design.md).

**Verificación:** `pytest tests/contrato -k "fuentes_config"`.
**Commit:** `feat(p1-contrato): declare raw sources configuration`

## T3 — Base fuente poblada

- [x] **Rojo (estática):** el servicio `src` del compose monta `./data/sgfood_oltp.sql` en `/docker-entrypoint-initdb.d/` como solo lectura.
- [x] **Rojo (integración):** `tests/contrato/test_base_fuente.py` exige:
  - En `src` existe el schema `oltp_sgfood` con exactamente 7 tablas.
  - Cada tabla tiene la cantidad de filas indicada en [design.md](design.md).
  - Las columnas de cada tabla coinciden en nombre y orden con las declaradas en `fuentes.yml`.
- [x] **Verde:** agregar el montaje al servicio `src` y reiniciar el entorno con `docker compose down -v` y `docker compose up -d`.
- [x] Confirmar que `data/sgfood_oltp.sql` no fue modificado.

**Verificación:** `pytest tests/contrato -k "base_fuente"`.
**Commit:** `feat(p1-contrato): seed source database with official oltp script`

## T4 — Tablas de `raw`

- [x] **Rojo (integración):** `tests/contrato/test_tablas_raw.py` exige:
  - El schema `raw` contiene exactamente las tablas declaradas en `fuentes.yml`.
  - Las columnas de negocio de cada tabla coinciden en nombre y orden con `fuentes.yml` y son de tipo `text`.
  - Cada tabla termina con `_loaded_at` (`timestamp with time zone`, no nula) y `_source` (`text`, no nula).
  - Ninguna tabla de `raw` tiene claves primarias, foráneas ni restricciones `CHECK` o `UNIQUE`.
  - Todas las tablas de `raw` están vacías.
  - Ejecutar `02_raw_tables.sql` por segunda vez con `ON_ERROR_STOP=1` termina sin error.
- [x] **Rojo (ajuste):** en `tests/entorno/test_schemas.py`, la prueba de schemas sin tablas pasa a exigir solo `staging` y `marts`.
- [x] **Verde:** crear `sql/ddl/02_raw_tables.sql` con `CREATE TABLE IF NOT EXISTS` y un comentario por tabla con su fuente de origen.

**Verificación:** reinicio limpio y `pytest tests/contrato -k "tablas_raw"` más `pytest tests/entorno -k "schemas"`.
**Commit:** `feat(p1-contrato): create raw tables`

## T5 — Documento de contrato

- [x] **Rojo:** `tests/contrato/test_documento_contrato.py` exige:
  - `docs/contrato_raw.md` existe y declara la misma versión que `fuentes.yml`.
  - Menciona cada `tabla_raw` y cada columna declarada en `fuentes.yml`.
  - No tiene una sección de tabla que `fuentes.yml` no declare.
  - Los conteos de filas del documento coinciden con los que usan las pruebas.
- [x] **Verde:** escribir `docs/contrato_raw.md` con la estructura de [design.md](design.md), tomando tipo, regla y descripción de cada campo del diccionario oficial.
- [x] Revisar a mano que las descripciones correspondan al diccionario; las pruebas no lo cubren.

**Verificación:** `pytest tests/contrato -k "documento_contrato"`.
**Commit:** `docs(p1-contrato): add raw contract v1`

## T6 — Arranque desde cero

- [x] Ejecutar `docker compose down -v` y `docker compose up -d` sin contenedores ni volúmenes previos.
- [x] Ejecutar la suite completa: `pytest tests/entorno tests/contrato`.
- [x] Ejecutar la prueba lenta de reinicio de forma explícita y confirmar que sigue pasando con la base fuente poblada.
- [x] Corregir tiempos de `healthcheck` o esperas si la carga del script de la fuente los afecta.

**Verificación:** todas las pruebas pasan en un entorno limpio; se registra la salida.
**Commit:** `test(p1-contrato): verify contract from clean start` (solo si hubo cambios)

## T7 — Documentación

- [x] Agregar al `README.md` una sección sobre los datos oficiales, la base fuente y el contrato, con enlace a `docs/contrato_raw.md`.
- [x] Actualizar en el `README.md` la sección de reinicio: los scripts de inicialización solo corren con volúmenes vacíos.
- [x] Marcar "Redactar y validar el contrato raw `v1`" en [architecture.md](../../steering/architecture.md).
- [x] Marcar en este documento solo lo observado.

**Verificación:** un integrante sigue el README en un clon limpio y llega a las 12 tablas de `raw` creadas.
**Commit:** `docs(p1-contrato): document source data and raw contract`

## Definición de terminado

- [x] Todos los escenarios Gherkin de [requirements.md](requirements.md) pasan.
- [x] `pytest tests/entorno tests/contrato` pasa completo en un entorno limpio.
- [x] `fuentes.yml`, el DDL y `contrato_raw.md` coinciden en tablas y columnas.
- [x] Los archivos de `data/` están versionados sin cambios de contenido.
- [ ] B validó el contrato `v1`.

## Fuera de esta feature

Código de extracción y carga, DAG, proyecto dbt y uso de los casos de calidad opcionales. Ver la tabla de alcance en [requirements.md](requirements.md).
