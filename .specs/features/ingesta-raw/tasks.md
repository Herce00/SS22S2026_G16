# Tareas — `ingesta-raw`

Diez tareas ordenadas para construir la ingesta con TDD: primero las piezas sin base de datos, después la carga real y al final los casos de fallo. **Ninguna se ejecuta hasta aprobar este documento.**

- **Requisitos:** [requirements.md](requirements.md)
- **Diseño:** [design.md](design.md)
- **Rol dueño:** A

Las rutas son relativas a `Proyecto1/` y los comandos se ejecutan desde esa carpeta. Los campos Rojo, Verde, Verificación y Commit significan lo mismo que en las features anteriores.

## Resumen

| # | Tarea | Requisitos | Depende de | Tipo de prueba |
|---|-------|-----------|-----------|----------------|
| T1 | Esqueleto del paquete y arnés | — | — | Unitaria |
| T2 | Lectura de la configuración | R1 | T1 | Unitaria |
| T3 | Extracción desde CSV | R3 | T2 | Unitaria |
| T4 | Consulta de extracción y conexiones | R2, R8.1, R8.2 | T2 | Unitaria |
| T5 | Carga de una tabla | R4, R7.1–R7.4, R8.3 | T3, T4 | Integración |
| T6 | Carga completa y auditoría | R6.1, R4.3, R4.4, R7.2 | T5 | Integración |
| T7 | Fidelidad y representación | R6.2, R6.3 | T6 | Integración |
| T8 | Idempotencia y fallos | R5, R4.2, R4.6, R8.4 | T6 | Integración |
| T9 | Arranque desde cero y evidencia | R7.5 | T7, T8 | Integración |
| T10 | Documentación | — | T9 | — |

Toda la feature es zona verde del rol A. No requiere acuerdos previos con B.

## T1 — Esqueleto del paquete y arnés

- [x] Confirmar que la rama activa es `feat/ingesta-airflow`.
- [x] **Rojo:** `tests/ingesta/test_config.py` con una prueba que importa `sgfood_ingesta` y exige que exponga `listar_fuentes`, `cargar_fuente` y `cargar_todas`. Falla porque el paquete no existe.
- [x] **Verde:** crear `python/sgfood_ingesta/` con sus módulos vacíos y `errores.py` con la jerarquía de excepciones de [design.md](design.md).
- [x] Agregar `pythonpath = python` a `pytest.ini` y `psycopg[binary]` a `tests/requirements-dev.txt` con la versión de `airflow/requirements.txt`.
- [x] **Rojo (estática):** `airflow/requirements.txt` no incluye `pandas`. **Verde:** retirarlo y reconstruir la imagen.

**Verificación:** `pytest tests/ingesta -m "not integracion"`.
**Commit:** `feat(p1-ingesta): add ingestion package skeleton`

## T2 — Lectura de la configuración

- [x] **Rojo:** pruebas unitarias sobre `config.py`:
  - Con el `fuentes.yml` real, devuelve 12 objetos `Fuente` en el orden declarado.
  - Archivo inexistente produce `ConfiguracionInvalida`.
  - Produce `ConfiguracionInvalida`: falta `version`, falta un campo, `tipo` desconocido, `tabla_raw` duplicado, columnas duplicadas, lista de columnas vacía, `origen` de tipo `postgres` sin schema.
  - `Fuente` es inmutable.
  - La ruta se toma de `SGFOOD_FUENTES_PATH` cuando está definida.
- [x] **Verde:** implementar `config.py`.

**Verificación:** `pytest tests/ingesta -k "config"`.
**Commit:** `feat(p1-ingesta): load and validate sources configuration`

## T3 — Extracción desde CSV

- [x] **Rojo:** crear `tests/ingesta/fixtures/` y pruebas unitarias sobre la lectura de CSV:
  - Un archivo con BOM devuelve el primer nombre de columna sin el carácter invisible.
  - Los valores salen como texto, sin conversión: `007` sigue siendo `007`, `1.50` sigue siendo `1.50`.
  - Un campo vacío sale como `None`; un campo con solo espacios conserva los espacios.
  - Encabezado distinto, o en otro orden, produce `EncabezadoInvalido`.
  - Una fila con un campo de menos o de más produce `FilaInvalida` con el número de línea.
  - Una línea completamente vacía se omite y no cuenta como fila.
  - Un campo entre comillas con una coma dentro se lee como un solo valor.
  - Con cada CSV real de `data/`, la cantidad de filas coincide con la del contrato.
- [x] **Verde:** implementar la lectura de CSV en `extraccion.py`.

**Verificación:** `pytest tests/ingesta -k "extraccion_csv"`.
**Commit:** `feat(p1-ingesta): extract rows from csv sources`

## T4 — Consulta de extracción y conexiones

- [x] **Rojo:** pruebas unitarias:
  - La consulta generada para una fuente `postgres` convierte cada columna con `::text`, respeta el orden declarado y califica la tabla con su schema.
  - Un nombre con comillas o punto y coma queda escapado como identificador y no altera la consulta.
  - `conexiones.py` arma los parámetros del DW y de la fuente desde el entorno.
  - Una variable faltante produce `ConfiguracionInvalida` nombrando la variable.
  - La representación en texto de los parámetros no incluye la contraseña.
- [x] **Verde:** implementar la construcción de la consulta en `extraccion.py` y `conexiones.py`.

**Verificación:** `pytest tests/ingesta -k "extraccion_postgres or conexiones"`.
**Commit:** `feat(p1-ingesta): build extraction query and connection settings`

## T5 — Carga de una tabla

- [x] **Rojo (estática):** los servicios de Airflow del compose definen `PYTHONPATH` con `/opt/airflow/python`.
- [x] **Rojo (integración):** `tests/ingesta/test_carga_tabla.py`:
  - `python -m sgfood_ingesta --tabla devoluciones` dentro de `airflow-scheduler` termina con código 0 y `raw.devoluciones` queda con 80 filas.
  - `python -m sgfood_ingesta --tabla sucursal` termina con código 0 y `raw.sucursal` queda con 6 filas.
  - Cargar una tabla no cambia la cantidad de filas de las demás.
  - `--tabla tabla_inexistente` termina con código 2 y lista las tablas válidas.
  - `--listar` muestra las 12 tablas.
  - La salida registra origen, destino, filas leídas, filas cargadas y duración, y no contiene la contraseña del DW.
- [x] **Verde:** implementar `carga.py`, `ingesta.py`, `cli.py` y `__main__.py`; agregar `PYTHONPATH` al compose.
- [x] Cerrar el punto abierto de [design.md](design.md) sobre `COPY` y valores `None`.

**Verificación:** recrear los servicios de Airflow y `pytest tests/ingesta -k "carga_tabla"`.
**Commit:** `feat(p1-ingesta): load a single source into raw`

## T6 — Carga completa y auditoría

- [x] **Rojo (integración):** `tests/ingesta/test_carga_completa.py`:
  - `python -m sgfood_ingesta` termina con código 0.
  - Cada tabla de `raw` tiene la cantidad de filas del contrato; el total es 8864.
  - En cada tabla, `_source` tiene un único valor, igual al `origen` de `fuentes.yml`.
  - Las 12 tablas comparten un único valor de `_loaded_at`.
  - Tras cargar después solo `devoluciones`, su `_loaded_at` es posterior y el de las demás no cambió.
  - Los conteos de `oltp_sgfood` no cambiaron y `staging` y `marts` siguen sin tablas.
- [x] **Rojo (ajuste):** retirar de `tests/contrato/test_tablas_raw.py` la comprobación de tablas vacías.
- [x] **Verde:** implementar `cargar_todas` con `loaded_at` compartido.

**Verificación:** `pytest tests/ingesta -k "carga_completa"` y `pytest tests/contrato`.
**Commit:** `feat(p1-ingesta): load all sources with shared audit timestamp`

## T7 — Fidelidad y representación

- [ ] **Rojo (integración):** `tests/ingesta/test_fidelidad.py`:
  - Para cada fuente `postgres`, las filas de la tabla fuente convertidas a texto y las columnas de negocio de `raw` son iguales como conjuntos con multiplicidad, en ambos sentidos.
  - Para cada fuente `csv`, las filas leídas del archivo en la prueba y las de `raw` son iguales como conjuntos con multiplicidad.
  - `producto.activo` solo contiene `true` o `false`.
  - `venta_detalle.descuento` cumple siempre el formato de cuatro decimales.
  - `venta.fecha`, `cliente.fecha_alta` e `inventario_bodega.fecha_corte` cumplen `YYYY-MM-DD`.
  - `metas_ventas.periodo` cumple `YYYY-MM`.
  - Los nulos de `cliente.municipio` y `cliente.departamento` en `raw` son tantos como en la fuente.
  - Ninguna columna de negocio de ninguna tabla contiene una cadena vacía.
- [ ] **Verde:** corregir lo que las pruebas revelen. Si todo pasa sin cambios, registrarlo.

**Verificación:** `pytest tests/ingesta -k "fidelidad"`.
**Commit:** `test(p1-ingesta): verify raw content matches sources`

## T8 — Idempotencia y fallos

- [ ] **Rojo (integración):** `tests/ingesta/test_idempotencia.py`:
  - Dos cargas completas seguidas dejan cada tabla con la misma cantidad de filas y el mismo contenido de negocio.
- [ ] **Rojo (integración):** `tests/ingesta/test_fallos.py`, con una carga completa previa y `SGFOOD_DATA_DIR` apuntando a una copia temporal de `fixtures/` dentro del contenedor:
  - Encabezado incorrecto en `promociones.csv`: código de salida 1 y `raw.promociones` conserva sus 30 filas y su `_loaded_at`.
  - Fila con un campo de menos: código de salida 1, mensaje con el número de línea y la tabla conserva sus 30 filas.
  - Archivo CSV inexistente: código de salida 1 y la tabla conserva sus filas.
  - En una carga completa donde falla una tabla, el proceso termina con código 1 y las tablas anteriores quedan confirmadas.
- [ ] **Rojo (unitaria):** con una carga cuyo conteo final no coincide con las filas enviadas, se lanza `ConteoInconsistente` y la transacción se revierte.
- [ ] **Verde:** implementar lo necesario para que la transacción se revierta en todos los casos.
- [ ] Confirmar que ningún archivo de `data/` fue modificado: `git status --short data/` vacío.

**Verificación:** `pytest tests/ingesta -k "idempotencia or fallos"`.
**Commit:** `feat(p1-ingesta): keep previous data when a load fails`

## T9 — Arranque desde cero y evidencia

- [ ] **Rojo (estática):** el healthcheck de `src` consulta `oltp_sgfood.venta_detalle`.
- [ ] **Verde:** actualizar el healthcheck de `src`.
- [ ] Ejecutar `docker compose down -v` y `docker compose up -d`, y luego `python -m sgfood_ingesta` dentro de `airflow-scheduler`.
- [ ] Ejecutar la suite completa: `pytest tests/entorno tests/contrato tests/ingesta`, y la prueba lenta de forma explícita.
- [ ] Ejecutar el paquete con `docker compose run --rm` sobre un contenedor nuevo, para comprobar que no depende del estado del scheduler.
- [ ] Guardar en `evidencia/` el registro de la carga completa y el resultado de una consulta con el conteo por tabla de `raw`.

**Verificación:** todas las pruebas pasan en un entorno limpio; los archivos de evidencia contienen la salida real.
**Commit:** `feat(p1-ingesta): verify clean start load and add evidence`

## T10 — Documentación

- [ ] Agregar al `README.md` la sección de scripts Python: estructura del paquete, flujo de una tabla, comandos, códigos de salida, limpieza técnica aplicada y manejo de fallos.
- [ ] Actualizar [tech-stack.md](../../steering/tech-stack.md): lectura de CSV con la biblioteca estándar y retiro de `pandas`.
- [ ] Marcar el punto de integración 3 como entregado en [architecture.md](../../steering/architecture.md).
- [ ] Marcar en este documento solo lo observado.

**Verificación:** un integrante sigue el README en un clon limpio y llega a las 8864 filas en `raw`.
**Commit:** `docs(p1-ingesta): document python ingestion`

## Definición de terminado

- [ ] Todos los escenarios Gherkin de [requirements.md](requirements.md) pasan.
- [ ] `pytest tests/entorno tests/contrato tests/ingesta` pasa completo en un entorno limpio.
- [ ] `raw` contiene 8864 filas repartidas según el contrato.
- [ ] El código no contiene nombres de tablas ni de columnas de negocio escritos a mano.
- [ ] Ningún archivo de `data/` fue modificado.
- [ ] La evidencia de la carga está en `evidencia/`.

## Fuera de esta feature

DAG y programación, validaciones contra `marts`, modelos dbt y casos de calidad opcionales. Ver la tabla de alcance en [requirements.md](requirements.md).
