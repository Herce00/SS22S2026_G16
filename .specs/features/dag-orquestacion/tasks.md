# Tareas — `dag-orquestacion`

Doce tareas ordenadas para construir el DAG con TDD: primero el módulo de validación, después el DAG por partes y al final el esqueleto dbt y la guía que dejan a B listo para arrancar. **Ninguna se ejecuta hasta aprobar este documento.**

- **Requisitos:** [requirements.md](requirements.md)
- **Diseño:** [design.md](design.md)
- **Rol dueño:** A

Las rutas son relativas a `Proyecto1/` y los comandos se ejecutan desde esa carpeta. Los campos Rojo, Verde, Verificación y Commit significan lo mismo que en las features anteriores.

## Resumen

| # | Tarea | Requisitos | Depende de | Zona |
|---|-------|-----------|-----------|------|
| T0 | Decisiones compartidas (cerrada) | — | — | Amarilla |
| T1 | Verificar la API de Airflow 3.3.2 | R8.1 | — | Verde |
| T2 | Validación de conteos | R3 | T0 | Verde |
| T3 | Validaciones SQL | R5 | T0 | Amarilla |
| T4 | DAG con tareas de carga | R1, R2, R7, R8 | T1 | Verde |
| T5 | Validación de la carga en el DAG | R3, R6 | T2, T4 | Verde |
| T6 | Tareas de dbt | R4 | T0, T5 | Amarilla |
| T7 | Validaciones finales en el DAG | R5 | T3, T6 | Amarilla |
| T8 | Fallos y concurrencia | R4.3, R4.4, R6 | T7 | Verde |
| T9 | Arranque desde cero y evidencia | R7.3 | T8 | Verde |
| T10 | Esqueleto del proyecto dbt y ejecución real | R9, R10.2 | T9 | Amarilla |
| T11 | Guía para B y documentación | R10.3 | T10 | Verde |

## T0 — Decisiones compartidas

**Cerrada el 2026-10-10.** B todavía no comenzó y pidió una base para arrancar. A definió los seis puntos de "Dependencias con el rol B" como punto de partida y quedaron en el steering como decisiones D9, D10 y D11. La implementación empieza en T1.

- [x] Definir los seis puntos de "Dependencias con el rol B" de [requirements.md](requirements.md).
- [x] Registrarlos en [architecture.md](../../steering/architecture.md).
- [x] Acordar que A arma el esqueleto del proyecto dbt.

## T1 — Verificar la API de Airflow 3.3.2

- [x] Confirmar contra la documentación oficial de la versión 3.3.2: importación del DAG y de las tareas Python, importación del operador de Bash, parámetros de programación y de pausa al crearse, y cómo leer el inicio de la ejecución desde el contexto de una tarea.
- [x] Anotar en [design.md](design.md) las importaciones y los nombres de parámetros confirmados.

**Verificación:** los puntos abiertos de [design.md](design.md) sobre Airflow quedan marcados, cada uno con su fuente.
**Commit:** `docs(p1-dag): confirm airflow 3.3.2 api for the dag`

## T2 — Validación de conteos

- [x] **Rojo (unitaria):** `tests/dag/test_validacion.py`:
  - `validar_conteos` con conteos que coinciden devuelve una entrada por fuente.
  - Con una tabla que no coincide lanza `ValidacionFallida` nombrando la tabla y ambas cantidades.
  - Con dos tablas que no coinciden, el mensaje nombra las dos.
- [x] **Rojo (integración):** tras una carga completa, `validar_conteos` ejecutada en el contenedor termina bien y registra 12 tablas y el total de 8864; tras borrar una fila de `raw.promociones`, falla nombrando `promociones`.
- [x] **Verde:** crear `python/sgfood_ingesta/validacion.py` con `contar_fuentes_y_raw` y `validar_conteos`; agregar `ValidacionFallida` a `errores.py`.
- [x] La prueba de integración restaura `raw.promociones` al terminar.

**Verificación:** `pytest tests/dag -k "validacion and conteos"`.
**Commit:** `feat(p1-dag): validate row counts between sources and raw`

## T3 — Validaciones SQL

- [x] **Rojo (unitaria):**
  - Carpeta inexistente o vacía: devuelve lista vacía y registra una advertencia.
  - Los archivos se ejecutan en orden alfabético y solo los de extensión `.sql`.
- [x] **Rojo (integración):** con las carpetas de `tests/dag/fixtures/`:
  - `validaciones_ok`: termina bien y devuelve un resultado con cero filas.
  - `validaciones_falla`: lanza `ValidacionFallida` nombrando el archivo e incluyendo las filas devueltas.
  - Con dos archivos que fallan, el error nombra los dos.
  - Una consulta que intenta escribir es rechazada.
- [x] **Verde:** implementar `validar_sql`; crear las carpetas de prueba y `sql/validaciones/dag/.gitkeep`.

**Verificación:** `pytest tests/dag -k "validacion and sql"`.
**Commit:** `feat(p1-dag): run sql validation files against the warehouse`

## T4 — DAG con tareas de carga

- [ ] **Rojo (estructura):** `tests/dag/test_estructura_dag.py`:
  - Airflow no reporta errores de importación.
  - Existe el DAG `sgfood_elt`, en pausa, con programación diaria y sin ejecución de periodos anteriores.
  - Una sola ejecución activa y cuatro tareas activas como máximo.
  - Hay una tarea `carga_raw.cargar_<tabla>` por cada fuente de `fuentes.yml`, y ninguna más.
  - Cada tarea de carga tiene 2 reintentos y tiempo límite.
  - El archivo del DAG no contiene nombres de tablas, SQL ni credenciales.
- [ ] **Rojo (ajuste):** `tests/entorno/test_airflow.py` pasa a exigir que el único DAG sea `sgfood_elt`; ajustar la comprobación final de `tests/entorno/test_ejecucion_tareas.py`.
- [ ] **Verde:** crear `airflow/dags/sgfood_elt.py` con las tareas de carga.
- [ ] **Rojo y verde (ejecución):** disparar el DAG y exigir que las 12 tareas de carga terminen en `success`, que `raw` tenga 8864 filas y un único `_loaded_at` igual al inicio de la ejecución.

**Verificación:** `pytest tests/dag -k "estructura"` y `pytest tests/entorno`.
**Commit:** `feat(p1-dag): add sgfood_elt dag with raw load tasks`

## T5 — Validación de la carga en el DAG

- [ ] **Rojo (estructura):** `validar_carga_raw` existe, depende de todas las tareas de carga, no tiene reintentos y tiene tiempo límite.
- [ ] **Rojo (ejecución):** en una ejecución completa, `validar_carga_raw` termina en `success` y su registro contiene el conteo por tabla y el total.
- [ ] **Verde:** agregar la tarea al DAG.

**Verificación:** `pytest tests/dag -k "estructura or ejecucion"`.
**Commit:** `feat(p1-dag): validate raw load inside the dag`

## T6 — Tareas de dbt

- [ ] **Rojo (estructura):** existen `dbt_deps`, `dbt_run` y `dbt_test`, en ese orden después de `validar_carga_raw`; usan `/opt/dbt-venv/bin/dbt`; `dbt_test` no tiene reintentos; ningún comando contiene `||` ni `; true`.
- [ ] **Rojo (ejecución):** crear `tests/dag/fixtures/dbt_ok/` y disparar el DAG con `dbt_project_dir` y `dbt_profiles_dir` apuntando a su copia en el contenedor:
  - `dbt_deps`, `dbt_run` y `dbt_test` terminan en `success`.
  - El modelo del proyecto de prueba existe en el schema `dag_test` con 6 filas.
  - El registro de `dbt_run` contiene la salida de dbt.
- [ ] **Verde:** agregar las tareas de dbt y los parámetros de ejecución al DAG.
- [ ] La prueba elimina el schema `dag_test` al terminar.

**Verificación:** `pytest tests/dag -k "ejecucion"`.
**Commit:** `feat(p1-dag): run dbt deps, run and test from the dag`

## T7 — Validaciones finales en el DAG

- [ ] **Rojo (estática):** el compose monta `./sql` en `/opt/airflow/sql` como solo lectura en los servicios de Airflow.
- [ ] **Rojo (estructura):** `validar_marts` existe, depende de `dbt_test` y no tiene reintentos.
- [ ] **Rojo (ejecución):**
  - Con `validaciones_dir` apuntando a `validaciones_ok`: `validar_marts` termina en `success`.
  - Con la carpeta predeterminada vacía: termina en `success` y su registro contiene la advertencia.
- [ ] **Verde:** agregar la tarea, el parámetro y el montaje.

**Verificación:** `pytest tests/dag -k "ejecucion"` y `pytest tests/entorno`.
**Commit:** `feat(p1-dag): run final sql validations from the dag`

## T8 — Fallos y concurrencia

- [ ] **Rojo (ejecución):** `tests/dag/test_fallos_dag.py`:
  - Con `dbt_modelo_roto`: `dbt_run` termina en `failed`; `dbt_test` y `validar_marts` quedan sin ejecutar; la ejecución termina en `failed`; `raw` conserva 8864 filas.
  - Con `dbt_prueba_falla`: `dbt_run` en `success`, `dbt_test` en `failed`, `validar_marts` sin ejecutar.
  - Con `validaciones_falla`: `validar_marts` en `failed` y su registro nombra el archivo.
  - Con dos ejecuciones disparadas seguidas: la segunda no inicia tareas hasta que la primera termina.
- [ ] **Verde:** corregir lo que las pruebas revelen. Si todo pasa sin cambios, registrarlo.
- [ ] Cada prueba comprueba el estado de cada tarea por separado y limpia sus ejecuciones.

**Verificación:** `pytest tests/dag -k "fallos"`.
**Commit:** `test(p1-dag): verify failure propagation and single active run`

## T9 — Arranque desde cero y evidencia

- [ ] Ejecutar `docker compose down -v` y `docker compose up -d`.
- [ ] **Rojo y verde:** tras el arranque y dos ciclos del scheduler, `sgfood_elt` existe, está en pausa y no tiene ejecuciones.
- [ ] Ejecutar la suite completa: `pytest tests/entorno tests/contrato tests/ingesta tests/dag`, y la prueba lenta de forma explícita.
- [ ] Ejecutar el DAG una vez con el proyecto de prueba `dbt_ok` y guardar en `evidencia/`, como `.txt`: tareas y dependencias del DAG, estado de cada tarea de la ejecución y registros de `dbt_run`, `dbt_test` y `validar_marts`.
- [ ] Confirmar con `git status` que los archivos de evidencia no quedaron ignorados.

**Verificación:** todas las pruebas pasan en un entorno limpio; la evidencia está versionada.
**Commit:** `feat(p1-dag): verify clean start and add run evidence`

## T10 — Esqueleto del proyecto dbt y ejecución real

Es la única tarea que escribe en `dbt_project/`, por la decisión D11. Se limita a lo que lista [design.md](design.md).

- [ ] Confirmar contra la documentación de dbt 1.12 la forma del macro `generate_schema_name` y de `env_var`, y cerrar ese punto abierto.
- [ ] **Rojo (estática):** `tests/dag/test_esqueleto_dbt.py`:
  - Existen `dbt_project.yml`, `profiles.yml`, el macro de schema, `_fuentes.yml` y el modelo de ejemplo.
  - `profiles.yml` no contiene contraseñas, hosts ni usuarios literales: todo sale de `env_var`.
  - Toda tabla de `raw` declarada como fuente en el proyecto dbt existe en `fuentes.yml`.
  - `models/` contiene un único archivo `.sql`, y ninguno en `intermediate/` ni `marts/`.
- [ ] **Rojo (integración):** con `raw` cargado, dentro de `airflow-scheduler`:
  - `dbt debug`, `dbt run` y `dbt test` sobre `dbt_project` terminan con código 0.
  - El modelo de ejemplo existe en el schema `staging` con 6 filas y su clave convertida a entero.
  - No existe ningún schema cuyo nombre contenga dos veces `staging` o `marts`.
- [ ] **Verde:** crear el esqueleto.
- [ ] **Rojo y verde (independencia):** agregar un modelo temporal al proyecto, disparar `sgfood_elt` con los parámetros predeterminados y exigir que el modelo exista en el DW y que `git status` no muestre cambios en `airflow/`, `python/` ni `sql/`. Eliminar el modelo temporal y su objeto en el DW al terminar.
- [ ] Disparar `sgfood_elt` con los parámetros predeterminados y guardar en `evidencia/` el estado de cada tarea y los registros de `dbt_run` y `dbt_test`.
- [ ] Confirmar que las pruebas de `tests/dag/` de las tareas anteriores siguen pasando sin depender del esqueleto.

**Verificación:** `pytest tests/dag` completo y ejecución del DAG en `success` con el proyecto real.
**Commit:** `feat(p1-dbt): add dbt project skeleton and run full pipeline`

## T11 — Guía para B y documentación

- [ ] Escribir `docs/guia_rol_b.md` con la estructura de [design.md](design.md).
- [ ] Ejecutar cada comando de la guía en un clon limpio y corregir lo que no funcione.
- [ ] Escribir `dbt_project/README.md`: qué es configuración, qué es ejemplo y qué decisiones quedan abiertas.
- [ ] Agregar al `README.md` la sección del DAG: grafo, tabla de tareas, reintentos y tiempos límite, parámetros de ejecución, cómo activarlo y dispararlo, y cómo leer una ejecución fallida.
- [ ] Documentar la convención de validaciones finales.
- [ ] Marcar los puntos de integración 4 y 5 en [architecture.md](../../steering/architecture.md) según lo entregado.
- [ ] Listar las capturas de pantalla que debe tomar un integrante: grafo del DAG y ejecución exitosa.
- [ ] Marcar en este documento solo lo observado.

**Verificación:** siguiendo solo la guía, se llega desde un clon limpio a `raw` cargado, dbt ejecutado y el DAG en una ejecución exitosa.
**Commit:** `docs(p1-dag): document pipeline orchestration and role B guide`

## Definición de terminado

- [ ] Todos los escenarios Gherkin de [requirements.md](requirements.md) pasan.
- [ ] `pytest tests/entorno tests/contrato tests/ingesta tests/dag` pasa completo en un entorno limpio.
- [ ] El archivo del DAG no contiene lógica de carga, SQL ni nombres de tablas.
- [ ] La evidencia de una ejecución completa está versionada.
- [ ] El pipeline corrió completo con el esqueleto del proyecto dbt real.
- [ ] Las pruebas del DAG pasan sin depender del contenido de `dbt_project/`.
- [ ] La guía para B se siguió paso a paso en un clon limpio.
- [ ] Un integrante tomó las capturas del grafo y de la ejecución.

## Fuera de esta feature

Modelos y pruebas dbt, contenido de las validaciones SQL, consultas analíticas, alertas y visualización. Ver la tabla de alcance en [requirements.md](requirements.md).
