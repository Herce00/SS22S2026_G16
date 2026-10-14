# Proyecto 1 — Pipeline ELT SG-Food

Pipeline de Extracción, Carga y Transformación (ELT) para SG-Food utilizando Python, Apache Airflow, dbt Core y PostgreSQL como Data Warehouse.

- **Curso:** Seminario de Sistemas 2 — USAC, Facultad de Ingeniería
- **Grupo:** 16

## Integrantes

| Integrante | Carnet | Rol |
|------------|--------|-----|
| Keneth Willard Lopez Ovalle | `202100106` | A — Ingesta y orquestación: infraestructura, Python, Airflow |
| César Rolando Hernández Palacios | `202000806` | B — Transformación y modelado: dbt, modelo dimensional, validaciones |

## Descripción del pipeline

```
BD transaccional (oltp_sgfood) ──┐
                                 ├─► Python (sgfood_ingesta) ─► raw ─► dbt staging ─► dbt intermediate ─► dbt marts
5 archivos CSV ──────────────────┘
                 Airflow (sgfood_elt): carga → validación de carga → dbt run → dbt test → validaciones finales
```

1. **Extracción y carga:** Python lee las 7 tablas de la base transaccional y los 5 archivos CSV, y las carga tal cual, como texto, en el schema `raw`.
2. **Transformación:** dbt convierte tipos y construye el modelo dimensional en `staging` y `marts`.
3. **Orquestación:** un DAG de Airflow ejecuta todo en orden, con reintentos, validaciones y control de errores.

## Estado del proyecto

| Componente | Estado | Dónde está documentado |
|------------|--------|------------------------|
| Entorno con Docker Compose | Terminado | [Manual de implementación](#manual-de-implementación), secciones 1 a 5 |
| Datos oficiales y contrato de `raw` | Terminado | Sección 6 y [docs/contrato_raw.md](docs/contrato_raw.md) |
| Extracción y carga con Python | Terminado | Sección 7 |
| DAG de Airflow | Terminado | Sección 8 |
| Esqueleto del proyecto dbt | Terminado | Sección 9 y [dbt_project/README.md](dbt_project/README.md) |
| Diseño dimensional | **Definido — Rol B** | [Modelo del Data Warehouse](#modelo-del-data-warehouse) |
| Modelos de staging dbt | **Implementados — Rol B** | [Estructura del proyecto dbt](#estructura-del-proyecto-dbt) |
| Modelos intermediate dbt | **Implementados — Rol B** | [Estructura del proyecto dbt](#estructura-del-proyecto-dbt) |
| Modelos marts dbt | **Implementados — Rol B** | [Estructura del proyecto dbt](#estructura-del-proyecto-dbt) |
| Pruebas y documentación dbt | **Implementadas — Rol B** | [Estructura del proyecto dbt](#estructura-del-proyecto-dbt) |
| Consultas analíticas y de validación | **Implementadas — Rol B** | [Consultas analíticas y validación](#consultas-analíticas-y-validación) |
| Justificación de diseño del modelo | **Definida — Rol B** | [Justificación de diseño](#justificación-de-diseño) |

El Rol B tiene su punto de partida en [docs/guia_rol_b.md](docs/guia_rol_b.md).

---

## Manual de implementación

Guía paso a paso para desplegar y verificar el entorno base del proyecto desde un clon limpio.

### 1. Requisitos previos

- **Docker Desktop** (Engine 20.10+ y Docker Compose v2.0+).
- **Git**.
- **Python 3.10+** (opcional, necesario únicamente para ejecutar las pruebas automatizadas de desarrollo desde el host).

### 2. Configuración de variables de entorno

Copie la plantilla de variables de entorno `.env.example` a `.env`:

```bash
cd Proyecto1
cp .env.example .env
```

En sistemas Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Edite `.env` y ajuste las contraseñas y puertos del host según sus necesidades. Las variables principales son:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DW_DB` | Nombre de la base de datos del Data Warehouse | `sgfood_dw` |
| `DW_USER` | Usuario del Data Warehouse | `dw_user` |
| `DW_PASSWORD` | Contraseña del usuario del DW | `cambiar_dw_pass` |
| `DW_PORT` | Puerto expuesto en el host para el DW | `5433` |
| `SRC_DB` | Nombre de la base de datos transaccional fuente | `sgfood_src` |
| `SRC_USER` | Usuario de la base de datos fuente | `src_user` |
| `SRC_PASSWORD` | Contraseña del usuario de la fuente | `cambiar_src_pass` |
| `SRC_PORT` | Puerto expuesto en el host para la fuente | `5434` |
| `AIRFLOW_DB_USER` | Usuario de la base de metadatos de Airflow | `airflow` |
| `AIRFLOW_DB_PASSWORD` | Contraseña de metadatos de Airflow | `cambiar_airflow_db_pass` |
| `AIRFLOW_ADMIN_USER` | Usuario administrador de la interfaz de Airflow | `admin` |
| `AIRFLOW_ADMIN_PASSWORD` | Contraseña del usuario administrador de Airflow | `cambiar_admin_pass` |
| `AIRFLOW_PORT` | Puerto expuesto en el host para Airflow UI / API | `8080` |
| `AIRFLOW_UID` | Identificador numérico de usuario en Linux | `50000` |

> **Nota de seguridad:** El archivo `.env` está expresamente excluido de Git y nunca debe versionarse.

### 3. Arranque del entorno

Construya las imágenes personalizadas e inicie todos los servicios en segundo plano:

```bash
docker compose up -d
```

Este comando:
1. Levanta las instancias PostgreSQL para el Data Warehouse (`dw`), la base fuente (`src`) y la base de metadatos (`airflow-db`).
2. El contenedor `dw` inicializa automáticamente los schemas `raw`, `staging` y `marts` a partir de `sql/ddl/01_schemas.sql`, y crea las 12 tablas vacías del schema `raw` a partir de `sql/ddl/02_raw_tables.sql`.
3. El contenedor `src` ejecuta el script oficial `data/sgfood_oltp.sql` montado en `/docker-entrypoint-initdb.d/01_oltp.sql:ro`, creando el schema `oltp_sgfood` y poblando sus 7 tablas transaccionales.
4. Inicia `airflow-init` para aplicar las migraciones de base de datos y crear el usuario administrador.
5. Una vez completado `airflow-init`, arranca el servidor web (`airflow-apiserver`), el programador (`airflow-scheduler`) y el procesador de DAGs (`airflow-dag-processor`).

### 4. Verificación del estado de los servicios

Compruebe que todos los servicios de larga duración estén en estado saludable (`healthy`):

```bash
docker compose ps
```

Todos los servicios deben reportar estado `healthy` o `running`, y `airflow-init` debe figurar como `Exited (0)`.

### 5. Acceso a los servicios

#### Data Warehouse (DW)
- **Host:** `localhost`
- **Puerto:** Valor configurado en `DW_PORT` (por defecto `5433`)
- **Base de datos:** `sgfood_dw`
- **Usuario:** `dw_user`
- **Schemas iniciales:** `raw` (12 tablas vacías creadas), `staging`, `marts`

Comprobación rápida con cliente `psql`:
```bash
psql -h localhost -p 5433 -U dw_user -d sgfood_dw
```

#### Base transaccional fuente (SRC)
- **Host:** `localhost`
- **Puerto:** Valor configurado en `SRC_PORT` (por defecto `5434`)
- **Base de datos:** `sgfood_src`
- **Usuario:** `src_user`
- **Schema poblado:** `oltp_sgfood` (7 tablas con 4.763 registros)

Consulta de validación con `psql`:
```bash
psql -h localhost -p 5434 -U src_user -d sgfood_src -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'oltp_sgfood';"
```

#### Interfaz Web y API de Apache Airflow
- **URL Web UI:** `http://localhost:8080` (o el puerto configurado en `AIRFLOW_PORT`)
- **Autenticación Web:** Gestionada por FAB (`FabAuthManager`). El formulario de login solicita el usuario (`AIRFLOW_ADMIN_USER`) y contraseña (`AIRFLOW_ADMIN_PASSWORD`) configurados en `.env`.
- **Autenticación REST API (Airflow 3):** Para consumir los endpoints de la API (por ejemplo `/api/v2/dags`), obtenga primero un token JWT mediante `POST /auth/token` enviando `{"username": "<usuario>", "password": "<contraseña>"}` con cabecera `Content-Type: application/json`. Luego envíe el token devuelto en la cabecera `Authorization: Bearer <access_token>`.
- **Endpoint de salud:** `http://localhost:8080/api/v2/monitor/health` (o el puerto configurado en `AIRFLOW_PORT`)
- **Execution API interna:** Los workers y el scheduler se comunican con el api-server a través de `http://airflow-apiserver:8080/execution/` autenticados mediante `AIRFLOW_JWT_SECRET`.

### 6. Datos oficiales y Contrato de la capa Raw

Los datos de origen del proyecto residen en `data/` y se versionan de forma binaria/literal byte a byte mediante `.gitattributes` (`data/* -text`):

1. **Base transaccional PostgreSQL (`sgfood_oltp.sql`):** 7 tablas en `oltp_sgfood` con un total de 4.763 registros (`sucursal`: 6, `categoria`: 8, `marca`: 10, `producto`: 80, `cliente`: 250, `venta`: 1.200, `venta_detalle`: 3.209).
2. **Archivos planos CSV:** 5 archivos de fuentes externas con un total de 4.101 registros (`inventario_bodega.csv`: 3.840, `proveedores_precios.csv`: 103, `devoluciones.csv`: 80, `metas_ventas.csv`: 48, `promociones.csv`: 30).
3. **Casos de calidad opcionales (`casos_calidad_opcionales.csv`):** 10 registros con anomalías sintéticas. Según la decisión D8 de steering, **no forman parte de la ingesta principal** y su utilización para auditorías de calidad queda bajo criterio de dbt (Rol B).

#### Contrato y Especificación Técnica
- **Contrato de datos v1:** [docs/contrato_raw.md](docs/contrato_raw.md) detalla granularidad, reglas de representación (`NULL`, formatos numéricos y fechas ISO), columnas de auditoría (`_loaded_at`, `_source`) y el diccionario de campos.
- **Configuración centralizada:** [python/config/fuentes.yml](python/config/fuentes.yml) actúa como la única fuente de verdad consumible por código para la definición de fuentes, tablas y columnas.
- **DDL de tablas raw:** [sql/ddl/02_raw_tables.sql](sql/ddl/02_raw_tables.sql) crea las 12 tablas en `raw` tipadas como `TEXT` con columnas de auditoría, sin claves ni restricciones que impidan la auditoría en dbt.

### 7. Ingesta Técnica de Datos (sgfood_ingesta)

El paquete `Proyecto1/python/sgfood_ingesta/` implementa la extracción y carga técnica de las 12 fuentes de datos hacia el schema `raw` del Data Warehouse `sgfood_dw`, garantizando fidelidad e idempotencia.

#### Estructura del paquete

```
Proyecto1/python/sgfood_ingesta/
├── __init__.py      # Exporta la interfaz pública (listar_fuentes, cargar_fuente, cargar_todas)
├── __main__.py      # Punto de entrada para invocación con python -m sgfood_ingesta
├── cli.py           # CLI con argparse, configuración de logging y códigos de salida (0, 1, 2)
├── config.py        # Carga inmutable y validación estricta de python/config/fuentes.yml
├── conexiones.py    # Gestión segura de parámetros y conexiones psycopg (enmascara credenciales)
├── extraccion.py    # Extracción streaming con psycopg.sql (Postgres) y csv stdlib (utf-8-sig)
├── carga.py         # Carga transaccional al DW: TRUNCATE + COPY FROM STDIN + verificación de conteos
└── errores.py       # Jerarquía de excepciones de dominio (heredan de ErrorIngesta)
```

#### Flujo de carga por tabla

1. **Resolución:** Lee la especificación de la tabla desde `fuentes.yml` sin nombres de negocio escritos a mano en el código.
2. **Extracción Streaming:**
   - **PostgreSQL:** Construye una consulta parametrizada con `psycopg.sql.Identifier`, proyectando cada columna con `::text` sobre la base fuente en modo solo lectura (`read_only=True`).
   - **Archivos CSV:** Lee línea por línea en streaming usando el módulo estándar `csv` con codificación `utf-8-sig`. Valida el encabezado contra el contrato y detecta inconsistencias en número de columnas con reporte exacto de línea.
3. **Limpieza técnica aplicada:**
   - La **única transformación** realizada en Python es la conversión de cadenas vacías `""` a `None` (SQL `NULL`).
   - Se preservan espacios en blanco y no se efectúan conversiones de tipos en Python (todas las columnas de negocio residen como `TEXT` en `raw`, delegando auditorías y conversiones a dbt en la capa `staging`).
   - No se utiliza `pandas` (eliminado de los requisitos para máxima velocidad y ligereza).
4. **Carga Transaccional en Data Warehouse:**
   - Se ejecuta dentro de un bloque de transacción en `sgfood_dw` con `autocommit=False`.
   - Se vacía la tabla con `TRUNCATE TABLE raw.<tabla>`.
   - Se cargan las filas vía `COPY raw.<tabla> (...) FROM STDIN`. La biblioteca `psycopg` 3 (`write_row`) serializa de forma nativa los valores `None` a `NULL` (`\N`).
   - Se agregan las columnas de auditoría: `_loaded_at` (marca de tiempo compartida en UTC) y `_source` (ruta u origen exacto declarado).
   - Se ejecuta una verificación antes de confirmar: `SELECT count(*) FROM raw.<tabla>`. Si el total coincide exactamente con las filas leídas, se hace `COMMIT`; si difiere, se lanza `ConteoInconsistente` y se revierte la transacción (`ROLLBACK`).
5. **Manejo de fallos y aislamiento:**
   - Si ocurre un fallo en una tabla, la transacción se revierte por completo preservando los datos previos de esa tabla.
   - En una carga completa de las 12 tablas, si una tabla posterior falla, las tablas ya confirmadas con anterioridad permanecen persistidas en el DW.

#### Comandos de ejecución

Desde el host (a través de los contenedores Docker):

```bash
# Carga completa de las 12 tablas con timestamp auditado compartido (8.864 filas en total)
docker compose exec airflow-scheduler python -m sgfood_ingesta

# Carga de una tabla individual
docker compose exec airflow-scheduler python -m sgfood_ingesta --tabla devoluciones

# Listado de fuentes configuradas
docker compose exec airflow-scheduler python -m sgfood_ingesta --listar

# Ejecución desacoplada en un contenedor efímero independiente
docker compose run --rm airflow-scheduler python -m sgfood_ingesta
```

#### Códigos de salida

| Código | Significado | Comportamiento |
|:---:|---|---|
| `0` | Éxito | Todas las cargas solicitadas se completaron y confirmaron. |
| `1` | Fallo en carga | Error durante la extracción, discrepancia de conteo o archivo inexistente. La tabla afectada se revierte. |
| `2` | Configuración / argumentos inválidos | Argumentos erróneos o tabla inexistente en `fuentes.yml`. |

### 8. Orquestación del Pipeline ELT (DAG sgfood_elt)

El DAG `sgfood_elt` (`airflow/dags/sgfood_elt.py`) automatiza el ciclo completo del pipeline ELT:

```mermaid
graph LR
    subgraph Ingesta Concurrente
        C1[cargar_categoria]
        C2[cargar_cliente]
        C3[...]
        C12[cargar_venta_detalle]
    end
    C1 --> V1[validar_carga_raw]
    C2 --> V1
    C3 --> V1
    C12 --> V1
    V1 --> D1[dbt_deps]
    D1 --> D2[dbt_run]
    D2 --> D3[dbt_test]
    D3 --> V2[validar_marts]
```

- **Programación:** Diaria (`@daily`), en pausa al crearse (`is_paused_upon_creation=True`), `catchup=False`.
- **Concurrencia:** `max_active_runs=1` (evita colisiones de carga simultánea) y `max_active_tasks=4`.

#### Tabla de tareas, reintentos y tiempos límite

| Tarea / Grupo | Tipo | Reintentos | Retardo reintento | Tiempo límite | Propósito |
|---|---|:---:|:---:|:---:|---|
| `carga_raw.cargar_<tabla>` (x12) | `@task` (Python) | 2 | 1 min | 10 min | Ingesta de cada fuente a `raw` con `_loaded_at` compartido. |
| `validar_carga_raw` | `@task` (Python) | 0 | - | 5 min | Verifica que conteo fuente == conteo raw para las 12 tablas. Falla de inmediato ante discrepancias. |
| `dbt_deps` | `BashOperator` | 2 | 1 min | 10 min | Descarga paquetes dbt si existe `packages.yml`. |
| `dbt_run` | `BashOperator` | 1 | 1 min | 20 min | Compila y ejecuta modelos de staging, intermediate y marts. |
| `dbt_test` | `BashOperator` | 0 | - | 20 min | Ejecuta pruebas de calidad dbt (unicidad, no-nulos, relaciones). |
| `validar_marts` | `@task` (Python) | 0 | - | 10 min | Ejecuta archivos SQL de validación de negocio en orden alfabético. Falla si alguna consulta devuelve filas. |

#### Parámetros configurables (`params`)

El DAG admite parámetros en tiempo de ejecución o disparo manual:
- `dbt_project_dir`: Ruta del proyecto dbt (por defecto `/opt/airflow/dbt_project`).
- `dbt_profiles_dir`: Ruta del perfil dbt (por defecto `/opt/airflow/dbt_project`).
- `validaciones_dir`: Carpeta de consultas SQL de validación de marts (por defecto `/opt/airflow/sql/validaciones/dag`).

#### Cómo activarlo y dispararlo

```bash
# Activar (despausar) el DAG
docker compose exec airflow-scheduler airflow dags unpause -y sgfood_elt

# Disparar ejecución con parámetros predeterminados
docker compose exec airflow-scheduler airflow dags trigger sgfood_elt

# Disparar con parámetros personalizados (JSON)
docker compose exec airflow-scheduler airflow dags trigger sgfood_elt --conf '{"dbt_project_dir": "/opt/airflow/dbt_project"}'
```

#### Cómo leer e investigar una ejecución fallida

1. **Desde la interfaz web de Airflow (UI):**
   - Acceda a `http://localhost:8080` con usuario y contraseña de `.env` (`AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD`).
   - Ingrese al DAG `sgfood_elt` y seleccione la vista **Grid** o **Graph**.
   - Identifique la tarea en estado rojo (`failed`). Haga clic en ella y presione **Logs** para ver el stack trace completo.
2. **Desde la línea de comandos (CLI):**
   ```bash
   # Listar últimas ejecuciones del DAG
   docker compose exec airflow-scheduler airflow dags list-runs -d sgfood_elt --limit 5

   # Consultar el log de una tarea fallida específica
   docker compose exec airflow-scheduler airflow tasks logs sgfood_elt <task_id> <dag_run_id>
   ```
3. **Causas típicas de fallo:**
   - En `carga_raw.*`: Base fuente inaccesible o CSV faltante.
   - En `validar_carga_raw`: Discrepancia en conteos entre origen y destino.
   - En `dbt_run`: Error de sintaxis SQL o tabla de origen faltante.
   - En `dbt_test`: Registros duplicados o valores nulos que violan las reglas dbt.
   - En `validar_marts`: Una consulta en `sql/validaciones/dag/` arrojó filas (inconsistencia de negocio).

#### Convención de validaciones finales (`sql/validaciones/dag/`)

- Las consultas deben guardarse en `Proyecto1/sql/validaciones/dag/`.
- Formato: archivos `.sql` con prefijo numérico indicando orden de ejecución (ej. `01_integridad.sql`, `02_totales.sql`).
- Semántica: **Toda consulta debe devolver 0 filas si el Data Warehouse es consistente**. Si devuelve una o más filas, la tarea `validar_marts` falla inmediatamente y registra las filas anómalas en el log.

#### Capturas de pantalla requeridas para la entrega / reporte

Para la entrega del proyecto, el integrante debe tomar las siguientes capturas desde la UI de Airflow (`http://localhost:8080`):
1. **Grafo completo del DAG (`Graph View`):** Mostrando la estructura completa desde `carga_raw` hasta `validar_marts`.
2. **Ejecución exitosa (`Grid View` o `Graph View` en verde):** Mostrando todas las tareas en estado `success` (verde oscuro) para una corrida completa del pipeline.


### 9. Proyecto de Transformación dbt (dbt_project)

El esqueleto inicial en `Proyecto1/dbt_project/` permite que el **Rol B** construya modelos de staging, intermediate y marts conectando directamente al DW vía PostgreSQL adapter:

- **Configuración central:** `dbt_project.yml` define materializaciones por carpeta (staging como vista, marts como tabla).
- **Conexión:** `profiles.yml` lee variables `DW_*` mediante `env_var`.
- **Macro de Schemas:** `macros/generate_schema_name.sql` garantiza que dbt escriba exactamente en los schemas `staging` y `marts`.
- **Fuentes:** `models/staging/_fuentes.yml` declara las 12 tablas de `raw`.
- **Ejemplo de Staging:** `models/staging/stg_oltp__sucursal.sql` demuestra el consumo con `source()`, casteo desde `TEXT` y pruebas en `_staging.yml`.

> Consulte la [Guía de Arranque para Rol B](docs/guia_rol_b.md) para detalles completos de ejecución local, desarrollo de nuevos modelos y convenciones.

### 10. Ejecución de pruebas automatizadas

El proyecto cuenta con un arnés completo de pruebas automatizadas en `tests/entorno/`, `tests/contrato/`, `tests/ingesta/` y `tests/dag/` utilizando `pytest`:

1. Instale las dependencias de prueba:
   ```bash
   pip install -r tests/requirements-dev.txt
   ```

2. Pruebas unitarias y de configuración (rápidas, sin Docker):
   ```bash
   pytest tests/ -m "not integracion and not lenta"
   ```

3. Suite completa de integración (con contenedores activos):
   ```bash
   pytest tests/entorno tests/contrato tests/ingesta tests/dag
   ```

4. Prueba lenta de ciclo limpio de reinicio (`down -v` / `up -d`):
   ```bash
   pytest tests/entorno/test_reinicio.py -m lenta
   ```

### 11. Reinicio a estado limpio

Para restablecer el entorno borrando volúmenes y datos persistidos:

```bash
docker compose down -v
docker compose up -d
```

> [!IMPORTANT]
> **Comportamiento de inicialización de volúmenes:** Los scripts ubicados en `/docker-entrypoint-initdb.d/` tanto en `dw` (`01_schemas.sql`, `02_raw_tables.sql`) como en `src` (`01_oltp.sql`) se ejecutan **únicamente cuando sus volúmenes nombrados (`dw_data` y `src_data`) están completamente vacíos**. Si se agregan o modifican scripts DDL con un entorno ya levantado, es obligatorio ejecutar `docker compose down -v` para recrear las bases de datos desde cero, o bien aplicar los scripts manualmente con `psql`.

### 12. Problemas frecuentes y resolución

- **Puerto del host ocupado (Bind failed / port is already allocated):**
  Si puertos como 5433, 5434 u 8080 están ocupados por otros servicios locales en el host, cambie los valores correspondientes en su archivo `.env` local (por ejemplo `DW_PORT=5443`, `SRC_PORT=5444`, `AIRFLOW_PORT=8089`). No modifique `docker-compose.yml`.
- **Los schemas no aparecen en el DW:**
  Los scripts de `/docker-entrypoint-initdb.d/` solo se ejecutan cuando el volumen de base de datos está vacío. Si se crearon antes de montar el script, ejecute un reinicio limpio con `docker compose down -v` y vuelva a iniciar.
- **Variable requerida faltante:**
  Si falta alguna variable obligatoria en `.env`, `docker compose config` o `docker compose up` fallará indicando el nombre exacto de la variable que debe definirse.

---

## Modelo del Data Warehouse

El Data Warehouse utiliza un **modelo dimensional tipo constelación**. La estrella principal corresponde al proceso de ventas y las estrellas complementarias corresponden a inventario, devoluciones, metas y precios de proveedores. Todas comparten dimensiones conformadas, principalmente `dim_fecha`, `dim_producto` y `dim_sucursal`.

Se utiliza una constelación porque cada proceso tiene una granularidad diferente. Mantener una tabla de hechos para cada proceso evita duplicar ventas, inventario o metas al realizar consultas analíticas.

```mermaid
erDiagram
    dim_fecha ||--o{ fct_ventas_linea : "fecha"
    dim_cliente ||--o{ fct_ventas_linea : "cliente"
    dim_sucursal ||--o{ fct_ventas_linea : "sucursal"
    dim_producto ||--o{ fct_ventas_linea : "producto"

    dim_fecha ||--o{ fct_inventario_snapshot : "fecha de corte"
    dim_sucursal ||--o{ fct_inventario_snapshot : "sucursal"
    dim_producto ||--o{ fct_inventario_snapshot : "producto"

    dim_fecha ||--o{ fct_devoluciones : "fecha"
    dim_producto ||--o{ fct_devoluciones : "producto"

    dim_fecha ||--o{ fct_metas_ventas : "periodo"
    dim_sucursal ||--o{ fct_metas_ventas : "sucursal"

    dim_fecha ||--o{ fct_precios_proveedor : "vigencia"
    dim_producto ||--o{ fct_precios_proveedor : "producto"

    dim_categoria ||--o{ dim_producto : "clasifica"
    dim_marca ||--o{ dim_producto : "identifica"
    dim_categoria ||--o{ dim_promocion : "aplica"
    dim_fecha ||--o{ dim_promocion : "inicio"
    dim_fecha ||--o{ dim_promocion : "fin"

    dim_fecha {
        int fecha_key PK
        date fecha
        int dia
        int mes
        string nombre_mes
        int trimestre
        int anio
        int semana_anio
        boolean es_fin_de_semana
    }

    dim_sucursal {
        int sucursal_key PK
        int id_sucursal UK
        string nombre
        string ciudad
        string departamento
    }

    dim_cliente {
        int cliente_key PK
        int id_cliente UK
        string nit
        string nombre
        string tipo_cliente
        string municipio
        string departamento
        date fecha_alta
    }

    dim_categoria {
        int categoria_key PK
        int id_categoria UK
        string nombre
    }

    dim_marca {
        int marca_key PK
        int id_marca UK
        string nombre
    }

    dim_producto {
        int producto_key PK
        int id_producto UK
        string sku UK
        string nombre
        int categoria_key FK
        int marca_key FK
        string unidad_medida
        decimal costo_base
        decimal precio_lista
        boolean activo
    }

    dim_promocion {
        int promocion_key PK
        int id_promocion UK
        string nombre
        int fecha_inicio_key FK
        int fecha_fin_key FK
        int categoria_key FK
        decimal porcentaje_descuento
    }

    fct_ventas_linea {
        string venta_linea_key PK
        bigint id_detalle UK
        bigint id_venta
        int fecha_key FK
        int cliente_key FK
        int sucursal_key FK
        int producto_key FK
        string canal
        string metodo_pago
        string estado
        int cantidad
        decimal precio_unitario
        decimal descuento
        decimal subtotal
        decimal importe_bruto
        decimal importe_descuento
    }

    fct_inventario_snapshot {
        string inventario_snapshot_key PK
        int fecha_key FK
        int sucursal_key FK
        int producto_key FK
        string lote
        date fecha_vencimiento
        int stock_disponible
        int stock_minimo
        int stock_maximo
        int stock_faltante
        int stock_sobrante
        boolean esta_bajo_minimo
        boolean esta_sobre_maximo
    }

    fct_devoluciones {
        int devolucion_key PK
        int id_devolucion UK
        int fecha_key FK
        bigint id_venta
        int producto_key FK
        int cantidad
        string motivo
    }

    fct_metas_ventas {
        string meta_key PK
        int periodo_key FK
        string periodo
        int sucursal_key FK
        decimal meta_ventas
        int meta_unidades
    }

    fct_precios_proveedor {
        string precio_proveedor_key PK
        int id_proveedor
        string proveedor
        int producto_key FK
        int fecha_key FK
        decimal costo_proveedor
        int plazo_dias
    }
```

### Dimensiones conformadas

| Dimensión | Granularidad | Clave primaria | Propósito |
|-----------|--------------|----------------|-----------|
| `dim_fecha` | Una fila por fecha calendario | `fecha_key` | Analizar todos los procesos por día, mes, trimestre y año |
| `dim_sucursal` | Una fila por sucursal | `sucursal_key` | Analizar ventas, inventario y metas por ubicación |
| `dim_cliente` | Una fila por cliente | `cliente_key` | Analizar ventas por cliente y segmento |
| `dim_producto` | Una fila por producto | `producto_key` | Analizar ventas, inventario, devoluciones y precios |
| `dim_categoria` | Una fila por categoría | `categoria_key` | Clasificar productos y analizar promociones |
| `dim_marca` | Una fila por marca | `marca_key` | Analizar el desempeño por marca |
| `dim_promocion` | Una fila por campaña | `promocion_key` | Describir campañas y su vigencia |

Las claves sustitutas (`*_key`) se utilizan en los hechos. Las claves naturales (`id_*`) se conservan en las dimensiones para trazabilidad con la capa `raw`.

### Tablas de hechos

| Tabla | Granularidad | Medidas principales | Dimensiones relacionadas |
|-------|--------------|---------------------|--------------------------|
| `fct_ventas_linea` | Una fila por línea de detalle de venta | `cantidad`, `precio_unitario`, `descuento`, `subtotal`, `importe_bruto`, `importe_descuento` | Fecha, cliente, sucursal y producto |
| `fct_inventario_snapshot` | Una fila por fecha de corte, sucursal, producto y lote | `stock_disponible`, `stock_minimo`, `stock_maximo`, `stock_faltante`, `stock_sobrante` | Fecha, sucursal y producto |
| `fct_devoluciones` | Una fila por devolución registrada | `cantidad` | Fecha y producto; conserva `id_venta` como referencia degenerada |
| `fct_metas_ventas` | Una fila por periodo mensual y sucursal | `meta_ventas`, `meta_unidades` | Fecha/periodo y sucursal |
| `fct_precios_proveedor` | Una fila por proveedor, producto y fecha de vigencia | `costo_proveedor`, `plazo_dias` | Fecha y producto |

### Columnas de las dimensiones

#### `dim_fecha`

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `fecha_key` | `INTEGER` | Clave sustituta en formato `YYYYMMDD` |
| `fecha` | `DATE` | Fecha calendario |
| `dia` | `INTEGER` | Día del mes |
| `mes` | `INTEGER` | Número del mes |
| `nombre_mes` | `VARCHAR` | Nombre del mes |
| `trimestre` | `INTEGER` | Trimestre del año |
| `anio` | `INTEGER` | Año |
| `semana_anio` | `INTEGER` | Número de semana |
| `es_fin_de_semana` | `BOOLEAN` | Indica si la fecha corresponde a sábado o domingo |

#### `dim_sucursal`

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `sucursal_key` | `INTEGER` | Clave sustituta |
| `id_sucursal` | `INTEGER` | Clave natural de `raw.sucursal` |
| `nombre` | `VARCHAR` | Nombre comercial |
| `ciudad` | `VARCHAR` | Ciudad |
| `departamento` | `VARCHAR` | Departamento |

#### `dim_cliente`

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `cliente_key` | `INTEGER` | Clave sustituta |
| `id_cliente` | `INTEGER` | Clave natural de `raw.cliente` |
| `nit` | `VARCHAR` | NIT ficticio del cliente |
| `nombre` | `VARCHAR` | Nombre del cliente |
| `tipo_cliente` | `VARCHAR` | Segmento o tipo de cliente |
| `municipio` | `VARCHAR` | Municipio |
| `departamento` | `VARCHAR` | Departamento |
| `fecha_alta` | `DATE` | Fecha de registro del cliente |

#### `dim_categoria`

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `categoria_key` | `INTEGER` | Clave sustituta |
| `id_categoria` | `INTEGER` | Clave natural de `raw.categoria` |
| `nombre` | `VARCHAR` | Nombre de la categoría |

#### `dim_marca`

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `marca_key` | `INTEGER` | Clave sustituta |
| `id_marca` | `INTEGER` | Clave natural de `raw.marca` |
| `nombre` | `VARCHAR` | Nombre de la marca |

#### `dim_producto`

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `producto_key` | `INTEGER` | Clave sustituta |
| `id_producto` | `INTEGER` | Clave natural de `raw.producto` |
| `sku` | `VARCHAR` | Código único del producto |
| `nombre` | `VARCHAR` | Nombre del producto |
| `categoria_key` | `INTEGER` | FK a `dim_categoria` |
| `marca_key` | `INTEGER` | FK a `dim_marca` |
| `unidad_medida` | `VARCHAR` | Unidad de comercialización |
| `costo_base` | `NUMERIC(12,2)` | Costo de referencia |
| `precio_lista` | `NUMERIC(12,2)` | Precio de lista |
| `activo` | `BOOLEAN` | Indica si el producto está activo |

#### `dim_promocion`

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `promocion_key` | `INTEGER` | Clave sustituta |
| `id_promocion` | `INTEGER` | Clave natural de `raw.promociones` |
| `nombre` | `VARCHAR` | Nombre de la campaña |
| `fecha_inicio_key` | `INTEGER` | FK a `dim_fecha` para el inicio |
| `fecha_fin_key` | `INTEGER` | FK a `dim_fecha` para el final |
| `categoria_key` | `INTEGER` | FK a `dim_categoria` |
| `porcentaje_descuento` | `NUMERIC(5,4)` | Descuento expresado entre 0 y 1 |

### Columnas de las tablas de hechos

#### `fct_ventas_linea`

**Granularidad:** una fila por línea de detalle de venta.

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `venta_linea_key` | `VARCHAR` | Clave sustituta o hash de la línea |
| `id_detalle` | `BIGINT` | Clave natural de `raw.venta_detalle` |
| `id_venta` | `BIGINT` | Identificador de la venta; dimensión degenerada |
| `fecha_key` | `INTEGER` | FK a `dim_fecha` |
| `cliente_key` | `INTEGER` | FK a `dim_cliente` |
| `sucursal_key` | `INTEGER` | FK a `dim_sucursal` |
| `producto_key` | `INTEGER` | FK a `dim_producto` |
| `canal` | `VARCHAR` | Canal de venta |
| `metodo_pago` | `VARCHAR` | Método de pago |
| `estado` | `VARCHAR` | Estado de la venta |
| `cantidad` | `INTEGER` | Unidades vendidas |
| `precio_unitario` | `NUMERIC(12,2)` | Precio aplicado por unidad |
| `descuento` | `NUMERIC(5,4)` | Descuento aplicado entre 0 y 1 |
| `subtotal` | `NUMERIC(14,2)` | Importe neto registrado |
| `importe_bruto` | `NUMERIC(14,2)` | `cantidad * precio_unitario` |
| `importe_descuento` | `NUMERIC(14,2)` | `importe_bruto * descuento` |

#### `fct_inventario_snapshot`

**Granularidad:** una fila por fecha de corte, sucursal, producto y lote.

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `inventario_snapshot_key` | `VARCHAR` | Clave sustituta o hash de la combinación natural |
| `fecha_key` | `INTEGER` | FK a `dim_fecha` |
| `sucursal_key` | `INTEGER` | FK a `dim_sucursal` |
| `producto_key` | `INTEGER` | FK a `dim_producto` |
| `lote` | `VARCHAR` | Identificador del lote |
| `fecha_vencimiento` | `DATE` | Fecha de vencimiento |
| `stock_disponible` | `INTEGER` | Existencia disponible |
| `stock_minimo` | `INTEGER` | Nivel mínimo permitido |
| `stock_maximo` | `INTEGER` | Nivel máximo permitido |
| `stock_faltante` | `INTEGER` | `GREATEST(stock_minimo - stock_disponible, 0)` |
| `stock_sobrante` | `INTEGER` | `GREATEST(stock_disponible - stock_maximo, 0)` |
| `esta_bajo_minimo` | `BOOLEAN` | Indica si el stock está por debajo del mínimo |
| `esta_sobre_maximo` | `BOOLEAN` | Indica si el stock supera el máximo |

#### `fct_devoluciones`

**Granularidad:** una fila por devolución registrada.

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `devolucion_key` | `INTEGER` | Clave sustituta |
| `id_devolucion` | `INTEGER` | Clave natural de `raw.devoluciones` |
| `fecha_key` | `INTEGER` | FK a `dim_fecha` |
| `id_venta` | `BIGINT` | Venta asociada; referencia degenerada |
| `producto_key` | `INTEGER` | FK a `dim_producto` |
| `cantidad` | `INTEGER` | Cantidad devuelta |
| `motivo` | `VARCHAR` | Motivo de la devolución |

#### `fct_metas_ventas`

**Granularidad:** una fila por periodo mensual y sucursal.

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `meta_key` | `VARCHAR` | Clave sustituta o hash de periodo y sucursal |
| `periodo_key` | `INTEGER` | FK a `dim_fecha`, usando el primer día del mes |
| `periodo` | `VARCHAR(7)` | Periodo original en formato `YYYY-MM` |
| `sucursal_key` | `INTEGER` | FK a `dim_sucursal` |
| `meta_ventas` | `NUMERIC(14,2)` | Meta monetaria |
| `meta_unidades` | `INTEGER` | Meta de unidades |

#### `fct_precios_proveedor`

**Granularidad:** una fila por proveedor, producto y fecha de vigencia.

| Columna | Tipo conceptual | Descripción |
|---------|-----------------|-------------|
| `precio_proveedor_key` | `VARCHAR` | Clave sustituta o hash de la combinación natural |
| `id_proveedor` | `INTEGER` | Identificador natural del proveedor |
| `proveedor` | `VARCHAR` | Nombre del proveedor |
| `producto_key` | `INTEGER` | FK a `dim_producto` |
| `fecha_key` | `INTEGER` | FK a `dim_fecha` |
| `costo_proveedor` | `NUMERIC(12,2)` | Costo ofrecido por el proveedor |
| `plazo_dias` | `INTEGER` | Tiempo de entrega en días |

La tabla de hechos principal es `fct_ventas_linea`, cuya clave natural es `id_detalle`. Los atributos `canal`, `metodo_pago` y `estado` se conservan como dimensiones degeneradas porque son atributos descriptivos de baja cardinalidad y no requieren dimensiones independientes.

Las promociones se modelan como `dim_promocion`. Debido a que la fuente no contiene una relación entre promoción y venta, no se agrega una FK de promoción a `fct_ventas_linea` sin una regla de asociación validada. Si se necesita analizar campañas por día, se podrá agregar posteriormente `bridge_promocion_fecha`.

### Relaciones principales

```text
fct_ventas_linea.fecha_key    -> dim_fecha.fecha_key
fct_ventas_linea.cliente_key  -> dim_cliente.cliente_key
fct_ventas_linea.sucursal_key -> dim_sucursal.sucursal_key
fct_ventas_linea.producto_key -> dim_producto.producto_key

fct_inventario_snapshot.fecha_key    -> dim_fecha.fecha_key
fct_inventario_snapshot.sucursal_key -> dim_sucursal.sucursal_key
fct_inventario_snapshot.producto_key -> dim_producto.producto_key

fct_metas_ventas.periodo_key  -> dim_fecha.fecha_key
fct_metas_ventas.sucursal_key -> dim_sucursal.sucursal_key
```

Lo que ya existe en el Data Warehouse `sgfood_dw`:

| Schema | Contenido actual | Lo crea |
|--------|------------------|---------|
| `raw` | 12 tablas con los datos oficiales, todas las columnas de negocio como texto | DDL (`sql/ddl/`) y carga con Python |
| `staging` | 12 vistas tipadas y limpiadas desde `raw`, con pruebas de calidad | dbt |
| `marts` | Vacío | dbt |

## Estructura del proyecto dbt

La capa `staging` ya está implementada como vistas en el schema `staging`. Estos modelos consumen las 12 fuentes declaradas en `_fuentes.yml`, convierten los valores de `TEXT` a tipos analíticos y no realizan joins.

```text
dbt_project/models/
├── staging/
│   ├── _fuentes.yml
│   ├── _staging.yml
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
├── intermediate/  # Implementado: joins y lógica reutilizable
└── marts/         # Implementado: dimensiones y hechos
```

### Transformaciones de staging

| Grupo | Modelos | Transformaciones |
|-------|---------|------------------|
| OLTP | `stg_oltp__sucursal`, `stg_oltp__categoria`, `stg_oltp__marca` | Conversión de identificadores a `INTEGER` y limpieza de nombres |
| OLTP | `stg_oltp__producto` | Conversión de identificadores, precios, costos y `activo` |
| OLTP | `stg_oltp__cliente` | Conversión de `id_cliente` y `fecha_alta`; limpieza de atributos |
| OLTP | `stg_oltp__venta` | Conversión de IDs y fecha; limpieza de canal, pago y estado |
| OLTP | `stg_oltp__venta_detalle` | Conversión de cantidades, precios, descuentos y subtotal |
| CSV | `stg_archivos__inventario_bodega` | Conversión de fechas, IDs y existencias; limpieza de lote |
| CSV | `stg_archivos__proveedores_precios` | Conversión de proveedor, producto, costo, plazo y vigencia |
| CSV | `stg_archivos__devoluciones` | Conversión de devolución, venta, producto, fecha y cantidad |
| CSV | `stg_archivos__metas_ventas` | Validación del periodo `YYYY-MM` y conversión de metas |
| CSV | `stg_archivos__promociones` | Conversión de IDs, fechas, categoría y descuento |

Las conversiones numéricas y de fechas son tolerantes: se valida el formato antes de convertirlo. Un valor inválido se convierte en `NULL` para que sea detectado por las pruebas de calidad, en lugar de detener silenciosamente la transformación.

### Capa intermediate

La capa `intermediate` se materializa como vistas en el schema `staging`. Su objetivo es centralizar joins y cálculos reutilizables antes de construir las dimensiones y los hechos de `marts`.

| Modelo | Propósito |
|--------|-----------|
| `int_ventas_linea` | Une el detalle de venta con la cabecera y calcula `importe_bruto` e `importe_descuento` |
| `int_inventario_snapshot` | Calcula faltantes, sobrantes y alertas de inventario |
| `int_devoluciones` | Estandariza las devoluciones para el hecho correspondiente |
| `int_metas_ventas` | Convierte el periodo `YYYY-MM` a una fecha mensual |
| `int_precios_proveedor` | Prepara los precios de proveedores para el hecho correspondiente |

Los modelos `intermediate` utilizan `ref()` sobre staging y no consultan directamente `raw`.

### Capa marts

La capa `marts` se materializa como tablas en el schema `marts`. Contiene las dimensiones conformadas y los hechos definidos en el modelo dimensional.

| Tipo | Modelos |
|------|---------|
| Dimensiones | `dim_fecha`, `dim_sucursal`, `dim_cliente`, `dim_categoria`, `dim_marca`, `dim_producto`, `dim_promocion` |
| Hechos | `fct_ventas_linea`, `fct_inventario_snapshot`, `fct_devoluciones`, `fct_metas_ventas`, `fct_precios_proveedor` |

Las dimensiones se construyen con claves sustitutas `*_key` y conservan las claves naturales `id_*`. Los hechos utilizan las claves sustitutas para relacionarse con las dimensiones. `fct_ventas_linea` conserva la granularidad de una fila por detalle de venta.

`fct_ventas_linea` se materializa como `incremental` usando `id_detalle` como `unique_key`; las demás dimensiones y hechos se materializan como tablas.

### Materialización y pruebas de staging

La configuración en [dbt_project.yml](dbt_project/dbt_project.yml) define:

```yaml
staging:
  +schema: staging
  +materialized: view
```

Las pruebas se encuentran en [models/staging/_staging.yml](dbt_project/models/staging/_staging.yml) e incluyen:

- `unique` y `not_null` para identificadores.
- `not_null` para campos obligatorios.
- `accepted_values` para `activo`, `canal`, `metodo_pago` y `estado`.

### Validación de la capa staging

Desde `Proyecto1/`, con Docker levantado y las fuentes cargadas en `raw`:

```powershell
docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt debug `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project

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

`dbt build` ejecuta los modelos y sus pruebas. La validación se considera exitosa cuando los 12 modelos compilan y las pruebas finalizan con estado `PASS`.

El punto de partida está en la sección 9 y en [dbt_project/README.md](dbt_project/README.md).

## Consultas analíticas y validación

Las consultas analíticas se encuentran en [sql/validaciones/](sql/validaciones/). Las consultas que deben detener el pipeline están en [sql/validaciones/dag/](sql/validaciones/dag/) y cumplen la convención de que **cero filas significa consistencia**.

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `01_conteos_marts.sql` | Analítica | Conteo de dimensiones y hechos |
| `02_ventas_por_sucursal.sql` | Analítica | Ventas, unidades e ingresos por sucursal |
| `03_metas_vs_ventas.sql` | Analítica | Comparación de ventas reales contra metas |
| `dag/01_integridad_referencial_marts.sql` | Control de pipeline | Detecta hechos sin dimensión relacionada |
| `dag/02_reglas_negocio_marts.sql` | Control de pipeline | Detecta cantidades o stocks inválidos |

La prueba personalizada de dbt [assert_ventas_subtotal_consistente.sql](dbt_project/tests/assert_ventas_subtotal_consistente.sql) valida que el subtotal sea consistente con el importe bruto y el descuento.

Validaciones que ya ejecuta el pipeline:

| Validación | Qué comprueba | Dónde |
|------------|---------------|-------|
| Conteo por tabla durante la carga | Filas cargadas en `raw` iguales a las leídas de la fuente; si no coinciden, la carga se revierte | `sgfood_ingesta` |
| `validar_carga_raw` | Filas de cada fuente iguales a las de su tabla en `raw`, para las 12 tablas | Tarea del DAG |
| `dbt_test` | Pruebas definidas en el proyecto dbt | Tarea del DAG |
| `validar_marts` | Cada consulta de `sql/validaciones/dag/` devuelve cero filas | Tarea del DAG |

Para generar la documentación navegable de dbt:

```powershell
docker compose exec airflow-scheduler `
  /opt/dbt-venv/bin/dbt docs generate `
  --project-dir /opt/airflow/dbt_project `
  --profiles-dir /opt/airflow/dbt_project
```

## Justificación de diseño

El diseño separa los procesos de negocio por su granularidad. Una línea de venta no representa un inventario ni una meta mensual; por eso cada proceso tiene su propia tabla de hechos. Las dimensiones conformadas permiten comparar los procesos usando las mismas definiciones de fecha, producto y sucursal.

La granularidad se declara antes de definir las medidas para evitar doble conteo. Por ejemplo, `fct_ventas_linea` se mantiene al nivel de `venta_detalle`, mientras que `fct_metas_ventas` se mantiene al nivel de mes y sucursal. Esto permite comparar ventas agregadas contra metas sin almacenar la meta repetida en cada línea.

Decisiones de la ingesta y la orquestación:

| Decisión | Motivo |
|----------|--------|
| ELT en lugar de ETL | Python solo extrae y carga; las reglas de negocio viven en dbt, donde quedan versionadas, probadas y documentadas |
| `raw` con todas las columnas como texto | Un valor inválido llega a `raw` y lo detecta una prueba dbt, en lugar de detener la carga |
| Truncado y recarga en una transacción por tabla | La carga es idempotente y, si falla, la tabla conserva los datos anteriores |
| Ingesta guiada por `fuentes.yml` | Agregar una fuente no requiere tocar código ni el DAG |
| Una tarea de Airflow por fuente | Reintento y registro por tabla |
| `dbt run` y `dbt test` como tareas separadas | Un fallo de modelo y uno de calidad de datos quedan distinguidos |
| dbt en un entorno virtual aislado | Evita conflictos de dependencias con Airflow |
| Validaciones finales como archivos SQL | Se agregan validaciones sin modificar el DAG |

## Evidencia de ejecución

Los archivos están en [evidencia/](evidencia/).

| Archivo | Contenido |
|---------|-----------|
| `carga_completa.txt` | Registro de una carga completa a `raw` |
| `conteo_tablas_raw.txt` | Filas por tabla de `raw` y total |
| `dag_tareas_y_dependencias.txt` | Tareas del DAG y sus dependencias |
| `dag_estados_tareas.txt` | Estado de cada tarea en una ejecución completa |
| `dag_log_dbt_run.txt`, `dag_log_dbt_test.txt`, `dag_log_validar_marts.txt` | Registros de las tareas de dbt y de validación |
| `dbt_run_ejecucion_real.txt` | Ejecución de dbt sobre el esqueleto del proyecto |
| `dbt_run_actual.txt` | Ejecución actual de los 29 modelos dbt: 17 vistas, 11 tablas y 1 incremental |
| `dbt_test_actual.txt` | Ejecución actual de las 154 pruebas dbt, todas aprobadas |
| `dbt_docs_generate_actual.txt` | Generación actual del catálogo y la documentación dbt |
| `validacion_01_conteos_marts_actual.txt` | Conteos actuales de dimensiones y hechos en `marts` |
| `validacion_02_ventas_sucursal_actual.txt` | Resultados actuales de ventas agrupadas por sucursal |
| `validacion_03_metas_vs_ventas_actual.txt` | Comparación actual de metas contra ventas reales |
| `validacion_dag_01_actual.txt` | Integridad referencial de los hechos hacia sus dimensiones; resultado: 0 filas |
| `validacion_dag_02_actual.txt` | Reglas de negocio de ventas, inventario y devoluciones; resultado: 0 filas |
| `dag_grafo.png` | Grafo del DAG `sgfood_elt` en la interfaz de Airflow |
| `dag_ejecucion_exitosa.png` | Ejecución completa con las 17 tareas en estado exitoso |
| `dag_ejecucion_actual.png` | Evidencia visual de la ejecución actual del DAG |
| `dag_fallo_controlado.png` | Ejecución detenida por una validación final que no se cumple |

### Grafo del DAG

El grupo `carga_raw` contiene las 12 tareas de carga, una por fuente. Después se ejecutan, en orden, `validar_carga_raw`, `dbt_deps`, `dbt_run`, `dbt_test` y `validar_marts`.

![Grafo del DAG sgfood_elt con el grupo carga_raw expandido](evidencia/dag_grafo.png)

### Validaciones actuales de los marts

Las validaciones finales que detienen el pipeline se encuentran en
[sql/validaciones/dag/](sql/validaciones/dag/). Cada consulta debe devolver cero
filas para considerar consistentes los datos:

- `01_integridad_referencial_marts.sql` verifica que las claves de fecha,
  cliente, sucursal y producto de los hechos existan en sus dimensiones.
- `02_reglas_negocio_marts.sql` verifica cantidades y subtotales positivos, así
  como valores de inventario no negativos.

La evidencia actual confirma que ambas consultas devolvieron `(0 rows)`:

- [validacion_dag_01_actual.txt](evidencia/validacion_dag_01_actual.txt)
- [validacion_dag_02_actual.txt](evidencia/validacion_dag_02_actual.txt)

### Ejecución exitosa

Ejecución manual del 2026-10-10 con los parámetros predeterminados: las 17 instancias de tarea terminaron en estado exitoso en 16 segundos.

![Ejecución del DAG sgfood_elt con las 17 tareas en estado exitoso](evidencia/dag_ejecucion_exitosa.png)

### Ejecución actual

La siguiente imagen corresponde a la ejecución actual del DAG `sgfood_elt`:

![Ejecución actual del DAG sgfood_elt](evidencia/dag_ejecucion_actual.png)

### Control de errores

Ejecución de prueba con una carpeta de validaciones cuyas consultas devuelven filas. La carga y las tareas de dbt terminan bien, `validar_marts` falla y la ejecución queda marcada como fallida. El registro nombra cada archivo de validación incumplido y muestra las filas devueltas.

![Tarea validar_marts fallida con el registro de la validación incumplida](evidencia/dag_fallo_controlado.png)

La evidencia de ejecución de Rol B conserva los resultados actuales de `dbt run`,
`dbt test`, `dbt docs generate`, las consultas analíticas y las validaciones
finales de [sql/validaciones/](sql/validaciones/). Los comandos reproducibles
están documentados en [dbt_project/README.md](dbt_project/README.md).
