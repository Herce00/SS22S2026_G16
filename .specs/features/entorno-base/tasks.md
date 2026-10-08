# Tareas — `entorno-base`

Diez tareas ordenadas para construir el entorno con TDD. Cada una indica la prueba que se escribe primero, la implementación mínima y cómo se verifica. **Ninguna se ejecuta hasta aprobar este documento.**

- **Requisitos:** [requirements.md](requirements.md)
- **Diseño:** [design.md](design.md)
- **Rol dueño:** A

## Cómo leer cada tarea

| Campo | Significado |
|-------|-------------|
| Rojo | Prueba que se escribe primero y debe fallar |
| Verde | Implementación mínima para que pase |
| Verificación | Comando que demuestra el resultado |
| Commit | Mensaje del commit que cierra la tarea |

Las rutas son relativas a `Proyecto1/`. Los comandos se ejecutan desde esa carpeta.

## Resumen

| # | Tarea | Requisitos | Depende de | Zona |
|---|-------|-----------|-----------|------|
| T0 | Acuerdos con B y rama de trabajo | — | — | Amarilla |
| T1 | Arnés de pruebas | — | T0 | Amarilla |
| T2 | Fijar versiones | R7 | T0 | Amarilla |
| T3 | Configuración y exclusiones | R6.1–R6.3, R1.3 | T1 | Verde |
| T4 | Servicios `dw` y `src` | R2, R1.2 | T3 | Verde |
| T5 | DDL de schemas | R3 | T4 | Verde |
| T6 | Imagen de Airflow con dbt | R5.1, R5.2, R7 | T2 | Verde |
| T7 | Servicios de Airflow | R1, R4 | T4, T6 | Verde |
| T8 | Conexiones y montajes | R5.3, R6.4, R6.5 | T7 | Verde |
| T9 | Reinicio limpio | R8 | T8 | Verde |
| T10 | Documentación | R7.3, R9 | T9 | Verde |

## T0 — Acuerdos con B y rama de trabajo

No produce código. Es requisito para el resto.

- [x] Validar con B los cinco puntos de "Dependencias con el rol B" de [requirements.md](requirements.md).
- [x] Registrar cualquier cambio acordado en [design.md](design.md) antes de continuar.
- [x] Crear la rama `feat/ingesta-airflow` desde `main`.
- [x] Confirmar que `.specs/` está versionado en la rama.

**Verificación:** `git branch --show-current` devuelve `feat/ingesta-airflow`.

## T1 — Arnés de pruebas

- [x] **Rojo:** `tests/entorno/test_config_estatica.py` con una prueba que exige que `docker compose config` termine con éxito. Falla porque no existe `docker-compose.yml`.
- [x] **Verde:** crear `tests/requirements-dev.txt` (versiones exactas de `pytest` y `PyYAML`), `tests/conftest.py` con los ayudantes para ejecutar `docker compose` y registrar los marcadores `integracion` y `lenta`.
- [x] La prueba queda en rojo de forma intencional hasta T4; se documenta en el propio archivo.

**Verificación:** `pytest tests/entorno -m "not integracion and not lenta"` se ejecuta y reporta la falla esperada.
**Commit:** `test(p1-entorno): add environment test harness`

## T2 — Fijar versiones

Las versiones ya están elegidas en [design.md](design.md); esta tarea comprueba que funcionan juntas.

- [x] Ejecutar `pip install --dry-run dbt-core==1.12.5 dbt-postgres==1.11.0` dentro de `apache/airflow:3.3.2-python3.12` y confirmar que se resuelven sin conflicto.
- [x] Si no se resuelven, elegir el parche de dbt Core 1.12 más reciente que sí lo haga y actualizar [design.md](design.md).
- [x] Confirmar la ruta del endpoint de salud en el `docker-compose.yaml` oficial de Airflow 3.3.2.
- [x] Fijar las versiones exactas de `pytest` y `PyYAML` para `tests/requirements-dev.txt`.

**Verificación:** la sección "Puntos abiertos" de [design.md](design.md) solo conserva la validación con B.
**Commit:** `docs(p1-entorno): pin environment versions`

## T3 — Configuración y exclusiones

- [x] **Rojo:** pruebas estáticas que exigen:
  - `.env.example` existe y contiene todas las variables de la tabla "Variables de `.env`" de [design.md](design.md).
  - `.gitignore` excluye `.env`, `logs/`, `target/` y `dbt_packages/`.
  - Ningún valor de `.env.example` coincide con un `.env` real presente.
- [x] **Verde:** crear `.env.example` y `.gitignore`.

**Verificación:** las pruebas nuevas pasan; `git check-ignore .env` devuelve la ruta.
**Commit:** `feat(p1-entorno): add env template and ignore rules`

## T4 — Servicios `dw` y `src`

- [x] **Rojo (estática):** el compose declara `dw` y `src`; ambas imágenes tienen etiqueta exacta distinta de `latest`; cada una tiene `healthcheck` y volumen con nombre; ningún valor de contraseña es literal; sin `DW_PASSWORD`, `docker compose config` falla nombrando la variable.
- [x] **Rojo (integración):** `dw` y `src` alcanzan el estado `healthy` y responden `SELECT 1`; están publicados en puertos del host distintos.
- [x] **Verde:** crear `docker-compose.yml` con los servicios `dw` y `src`.

**Verificación:** `docker compose up -d dw src` y `pytest tests/entorno -k "bases"`.
**Commit:** `feat(p1-entorno): add warehouse and source postgres services`

## T5 — DDL de schemas

- [x] **Rojo (integración):**
  - En `dw` existen los schemas `raw`, `staging` y `marts`.
  - Ninguno de los tres contiene tablas.
  - El usuario del DW puede crear una tabla en cada schema.
  - Ejecutar el script por segunda vez termina sin error.
- [x] **Verde:** crear `sql/ddl/01_schemas.sql` y montarlo en `/docker-entrypoint-initdb.d/` de `dw`.

**Verificación:** `docker compose down -v`, `docker compose up -d dw` y `pytest tests/entorno -k "schemas"`.
**Commit:** `feat(p1-entorno): create raw, staging and marts schemas`

## T6 — Imagen de Airflow con dbt

- [x] **Rojo (estática):** `airflow/Dockerfile` parte de una imagen con etiqueta exacta; `requirements.txt` y `requirements-dbt.txt` fijan cada paquete con `==`; `requirements.txt` no incluye `apache-airflow` ni `dbt`.
- [x] **Rojo (integración):** dentro de la imagen construida, `airflow version` devuelve `3.3.2`; `dbt --version` reporta dbt Core `1.12.5` y el adaptador `postgres` `1.11.0`; `dbt` se resuelve en `/opt/dbt-venv`.
- [x] **Verde:** crear `airflow/Dockerfile`, `airflow/requirements.txt` y `airflow/requirements-dbt.txt`.

**Verificación:** `docker compose build` y `pytest tests/entorno -k "imagen"`.
**Commit:** `feat(p1-entorno): build airflow image with isolated dbt`

## T7 — Servicios de Airflow

- [x] **Rojo (estática):** el compose declara `airflow-db`, `airflow-init`, `airflow-apiserver`, `airflow-scheduler` y `airflow-dag-processor`; el ejecutor es `LocalExecutor`; los DAGs de ejemplo están desactivados; no hay servicios `redis`, `worker` ni `flower`; los servicios de Airflow dependen de `airflow-init` completado.
- [x] **Rojo (integración):** todos los servicios de larga duración quedan `healthy`; `airflow-init` termina con código 0; el endpoint de salud responde en `AIRFLOW_PORT`; la lista de DAGs está vacía.
- [x] **Verde:** agregar los servicios de Airflow al compose y crear `airflow/dags/.gitkeep`.
- [x] La prueba de T1 pasa a verde.

**Verificación:** `docker compose up -d` y `pytest tests/entorno -k "airflow"`.
**Commit:** `feat(p1-entorno): add airflow services with local executor`

## T8 — Conexiones y montajes

- [x] **Rojo (integración):**
  - Dentro de `airflow-scheduler` existen `DW_HOST`, `DW_PORT`, `DW_DB`, `DW_USER`, `DW_PASSWORD` y sus equivalentes `SRC_`.
  - Con esas variables, una consulta `SELECT 1` responde contra `dw` y contra `src`.
  - `airflow connections get sgfood_dw` y `airflow connections get sgfood_src` devuelven la conexión.
  - Existen `/opt/airflow/dags`, `/opt/airflow/python`, `/opt/airflow/dbt_project` y `/opt/airflow/data`.
  - `DBT_PROJECT_DIR` y `DBT_PROFILES_DIR` están definidas.
- [x] **Verde:** agregar variables, conexiones `AIRFLOW_CONN_*` y montajes al compose; crear `python/.gitkeep` y `data/.gitkeep`.

**Verificación:** `pytest tests/entorno -k "conexiones or montajes"`.
**Commit:** `feat(p1-entorno): wire airflow connections and mounts`

## T9 — Reinicio limpio

- [ ] **Rojo (lenta):** `tests/entorno/test_reinicio.py` crea una tabla temporal en `dw`, ejecuta `docker compose down -v` y `docker compose up -d`, y exige que la tabla no exista, que los tres schemas existan y que todos los servicios queden `healthy`.
- [ ] **Verde:** ajustar volúmenes, dependencias o tiempos de `healthcheck` que la prueba revele.
- [ ] Ejecutar la suite completa desde un entorno sin contenedores ni volúmenes.

**Verificación:** `pytest tests/entorno` completo, incluidas las pruebas lentas.
**Commit:** `test(p1-entorno): verify clean restart`

## T10 — Documentación

- [ ] Actualizar la tabla "Versiones" de [tech-stack.md](../../steering/tech-stack.md) con las versiones fijadas.
- [ ] Marcar como resuelto "Verificar y fijar las versiones del entorno" en [architecture.md](../../steering/architecture.md).
- [ ] Escribir en `README.md` la sección "Manual de implementación": requisitos previos, creación de `.env`, arranque, verificación, acceso a cada servicio, ejecución de pruebas, reinicio y problemas frecuentes.
- [ ] Seguir el manual paso a paso en un clon limpio y corregir lo que no funcione.

**Verificación:** el manual se completa sin pasos fuera del documento.
**Commit:** `docs(p1-entorno): add implementation manual and pinned versions`

## Definición de terminado

- [ ] Todos los escenarios Gherkin de [requirements.md](requirements.md) pasan.
- [ ] `pytest tests/entorno` pasa completo en un entorno limpio.
- [ ] Ningún archivo versionado contiene credenciales ni la etiqueta `latest`.
- [ ] B confirmó que puede conectarse al DW y ver los tres schemas.
- [ ] Pull request de `feat/ingesta-airflow` hacia `main` abierto para revisión de B.

## Fuera de esta feature

Tablas de `raw`, datos de muestra, scripts de ingesta, DAGs y proyecto dbt. Ver la tabla de alcance en [requirements.md](requirements.md).
