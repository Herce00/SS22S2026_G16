# Requisitos — `entorno-base`

Entorno reproducible del Proyecto 1: un solo comando levanta el Data Warehouse, la base transaccional fuente y Airflow, con los tres schemas creados y dbt disponible. Es la primera feature porque desbloquea el trabajo de los dos integrantes y no depende del archivo de datos.

- **Rol dueño:** A (ingesta y orquestación)
- **Steering:** [architecture.md](../../steering/architecture.md) · [tech-stack.md](../../steering/tech-stack.md) · [coding-standards.md](../../steering/coding-standards.md)
- **Siguientes documentos:** [design.md](design.md) · [tasks.md](tasks.md)

## Problema

Hoy no existe un entorno común. Sin él, A no puede probar cargas ni DAGs, y B no puede ejecutar dbt contra un DW con los schemas acordados. Las versiones tampoco están fijadas (decisión D7).

## Casos de uso

| ID | Actor | Caso de uso | Resultado |
|----|-------|-------------|-----------|
| CU1 | Cualquier integrante | Levantar el entorno desde un clon limpio | DW, BD fuente y Airflow en ejecución y saludables |
| CU2 | Rol B | Conectar dbt al DW | dbt encuentra los schemas `raw`, `staging` y `marts` |
| CU3 | Rol A | Ejecutar tareas de Airflow contra DW y BD fuente | Los contenedores de Airflow resuelven ambas conexiones |
| CU4 | Cualquier integrante | Reiniciar el entorno a un estado limpio | Los datos se eliminan y el entorno vuelve a crearse igual |
| CU5 | Evaluador | Seguir el manual de implementación | Reproduce el entorno sin pasos no documentados |

## Alcance

**Incluye:**

- Versiones fijadas de Python, Airflow, PostgreSQL y dbt.
- `docker-compose.yml` con DW, BD transaccional fuente y Airflow.
- Imagen de Airflow con dbt instalado de forma aislada.
- `.env.example` y reglas de exclusión para archivos sensibles y generados.
- DDL de los schemas `raw`, `staging` y `marts`.
- Conexiones de Airflow hacia DW y BD fuente, definidas por configuración.
- Pruebas automáticas del entorno.
- Sección del manual de implementación en el README.

**No incluye (otras features):**

| Fuera de alcance | Feature prevista |
|------------------|------------------|
| Tablas de `raw` y contrato raw | `contrato-raw-v0` |
| Datos de muestra y tablas de la BD fuente | `contrato-raw-v0` / `ingesta-raw` |
| Scripts Python de extracción y carga | `ingesta-raw` |
| DAGs | `dag-orquestacion` |
| Proyecto dbt, `profiles.yml`, modelos y pruebas | Rol B |

## Requisitos (EARS)

### R1 — Arranque con un comando

- **R1.1** Cuando un integrante ejecute `docker compose up -d` con un archivo `.env` válido, el sistema deberá iniciar todos los servicios sin pasos manuales adicionales.
- **R1.2** Cuando todos los servicios hayan iniciado, el sistema deberá reportar el estado `healthy` en cada servicio de larga duración.
- **R1.3** Si falta el archivo `.env` o una variable obligatoria, entonces el sistema deberá fallar al iniciar con un mensaje que nombre la variable faltante.

### R2 — Bases de datos separadas

- **R2.1** El sistema deberá ejecutar el DW, la BD transaccional fuente y la base de metadatos de Airflow en instancias PostgreSQL independientes.
- **R2.2** El sistema deberá exponer el DW y la BD fuente en puertos del host distintos y configurables.
- **R2.3** El sistema deberá conservar los datos de las bases entre reinicios de contenedores.

### R3 — Schemas del DW

- **R3.1** Cuando el DW se inicialice por primera vez, el sistema deberá crear los schemas `raw`, `staging` y `marts`.
- **R3.2** El script DDL deberá poder ejecutarse más de una vez sin producir errores ni cambios.
- **R3.3** El sistema no deberá crear tablas de negocio en esta feature.

### R4 — Airflow operativo

- **R4.1** Cuando el entorno esté saludable, el sistema deberá servir la interfaz de Airflow en un puerto del host configurable.
- **R4.2** El sistema deberá cargar los DAGs desde `Proyecto1/airflow/dags/`.
- **R4.3** El sistema deberá ejecutar las tareas sin requerir servicios adicionales de mensajería.
- **R4.4** El sistema no deberá cargar los DAGs de ejemplo de Airflow.

### R5 — dbt disponible para Airflow

- **R5.1** El sistema deberá ofrecer el comando `dbt` con el adaptador de PostgreSQL dentro de los contenedores de Airflow.
- **R5.2** El sistema deberá instalar dbt aislado de las dependencias de Airflow.
- **R5.3** El sistema deberá montar `Proyecto1/dbt_project/` dentro de los contenedores de Airflow.

### R6 — Configuración y secretos

- **R6.1** El sistema deberá leer credenciales, nombres de base de datos y puertos desde variables de entorno.
- **R6.2** El repositorio deberá incluir un `.env.example` con todas las variables requeridas y valores de ejemplo no sensibles.
- **R6.3** El repositorio no deberá contener el archivo `.env` real ni credenciales escritas en archivos versionados.
- **R6.4** El sistema deberá exponer a los contenedores de Airflow las variables de conexión al DW y a la BD fuente.
- **R6.5** El sistema deberá registrar en Airflow una conexión al DW y otra a la BD fuente sin configuración manual en la interfaz.

### R7 — Versiones fijadas

- **R7.1** Toda imagen y toda dependencia Python deberá declarar una versión exacta.
- **R7.2** El sistema no deberá usar la etiqueta `latest`.
- **R7.3** Las versiones fijadas deberán quedar registradas en [tech-stack.md](../../steering/tech-stack.md).

### R8 — Reinicio limpio

- **R8.1** Cuando un integrante ejecute `docker compose down -v` seguido de `docker compose up -d`, el sistema deberá volver al mismo estado inicial.

### R9 — Documentación

- **R9.1** El README deberá describir requisitos previos, arranque, verificación, acceso a cada servicio y reinicio del entorno.

## Criterios de aceptación (Gherkin)

```gherkin
Característica: Entorno base del Proyecto 1

  Escenario: Arranque desde un clon limpio
    Dado un clon del repositorio sin contenedores ni volúmenes previos
    Y un archivo .env creado a partir de .env.example
    Cuando ejecuto "docker compose up -d" en Proyecto1
    Entonces todos los servicios de larga duración quedan en estado "healthy"
    Y la interfaz de Airflow responde en el puerto configurado

  Escenario: Schemas del Data Warehouse
    Dado el entorno en ejecución
    Cuando consulto los schemas del DW
    Entonces existen "raw", "staging" y "marts"
    Y ninguno contiene tablas

  Escenario: DDL reejecutable
    Dado el entorno en ejecución
    Cuando ejecuto el script DDL de schemas por segunda vez
    Entonces termina sin errores
    Y los schemas siguen siendo los mismos

  Escenario: dbt disponible en Airflow
    Dado el entorno en ejecución
    Cuando ejecuto "dbt --version" dentro de un contenedor de Airflow
    Entonces el resultado lista el adaptador "postgres"
    Y las versiones de dbt Core y del adaptador coinciden con las registradas en tech-stack.md

  Escenario: Conexiones desde Airflow
    Dado el entorno en ejecución
    Cuando un contenedor de Airflow abre una conexión al DW y otra a la BD fuente con las variables de entorno
    Entonces ambas conexiones responden a una consulta trivial
    Y Airflow lista las conexiones del DW y de la BD fuente

  Escenario: Variable obligatoria ausente
    Dado un archivo .env sin la contraseña del DW
    Cuando ejecuto "docker compose config"
    Entonces el comando falla nombrando la variable faltante

  Escenario: Sin secretos ni versiones flotantes
    Cuando reviso los archivos versionados de Proyecto1
    Entonces ninguna imagen usa la etiqueta "latest"
    Y el archivo .env está excluido del control de versiones
    Y docker-compose.yml no contiene contraseñas literales

  Escenario: Reinicio limpio
    Dado el entorno en ejecución con una tabla temporal creada en el DW
    Cuando ejecuto "docker compose down -v" y luego "docker compose up -d"
    Entonces la tabla temporal ya no existe
    Y los schemas "raw", "staging" y "marts" existen
```

## Dependencias con el rol B (zona amarilla)

Estos puntos deben validarse con B antes de implementar; hoy son propuesta de A.

| Tema | Propuesta | Detalle en |
|------|-----------|-----------|
| Versiones del entorno | Airflow 3.3.2, Python 3.12, PostgreSQL 16, dbt Core 1.12.5, `dbt-postgres` 1.11.0 | [design.md](design.md) |
| Nombres de las bases de datos | `sgfood_dw`, `sgfood_src` | [design.md](design.md) |
| Nombres de variables de entorno | Prefijos `DW_` y `SRC_` | [design.md](design.md) |
| Carpeta `Proyecto1/tests/` | Nueva en la estructura acordada | [design.md](design.md) |
| Ruta de montaje del proyecto dbt | `/opt/airflow/dbt_project` | [design.md](design.md) |

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| Memoria insuficiente en Docker Desktop (Airflow recomienda 4 GB) | Ejecutor local y solo los servicios necesarios |
| Conflicto de dependencias entre Airflow y dbt | dbt en un entorno virtual propio dentro de la imagen |
| dbt Core (1.12.5) y `dbt-postgres` (1.11.0) tienen números de versión distintos | Se fijan por separado y se comprueba que se resuelven juntas antes de construir la imagen |
| Diferencias de permisos de archivos entre Windows y Linux | `AIRFLOW_UID` configurable en `.env` |
