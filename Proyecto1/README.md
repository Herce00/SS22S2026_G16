# Proyecto 1 — Pipeline ELT SG-Food

Pipeline de Extracción, Carga y Transformación (ELT) para SG-Food utilizando Python, Apache Airflow, dbt Core y PostgreSQL como Data Warehouse.

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

### 7. Ejecución de pruebas automatizadas

El proyecto cuenta con un arnés de pruebas automatizadas en `tests/entorno/` y `tests/contrato/` utilizando `pytest`.

Para ejecutarlas desde el host:

1. Instale las dependencias de prueba:
   ```bash
   pip install -r tests/requirements-dev.txt
   ```

2. Ejecute las pruebas estáticas de contrato y configuración:
   ```bash
   pytest tests/contrato tests/entorno -m "not integracion and not lenta"
   ```

3. Ejecute la suite completa de integración de entorno y contrato:
   ```bash
   pytest tests/entorno tests/contrato
   ```

4. Para ejecutar de manera explícita la prueba de reinicio limpio (`down -v` y ciclo de reinicio de contenedores):
   ```bash
   pytest tests/entorno/test_reinicio.py -m lenta
   ```

### 8. Reinicio a estado limpio

Para restablecer el entorno borrando volúmenes y datos persistidos:

```bash
docker compose down -v
docker compose up -d
```

> [!IMPORTANT]
> **Comportamiento de inicialización de volúmenes:** Los scripts ubicados en `/docker-entrypoint-initdb.d/` tanto en `dw` (`01_schemas.sql`, `02_raw_tables.sql`) como en `src` (`01_oltp.sql`) se ejecutan **únicamente cuando sus volúmenes nombrados (`dw_data` y `src_data`) están completamente vacíos**. Si se agregan o modifican scripts DDL con un entorno ya levantado, es obligatorio ejecutar `docker compose down -v` para recrear las bases de datos desde cero, o bien aplicar los scripts manualmente con `psql`.

### 9. Problemas frecuentes y resolución

- **Puerto del host ocupado (Bind failed / port is already allocated):**
  Si puertos como 5433, 5434 u 8080 están ocupados por otros servicios locales en el host, cambie los valores correspondientes en su archivo `.env` local (por ejemplo `DW_PORT=5443`, `SRC_PORT=5444`, `AIRFLOW_PORT=8089`). No modifique `docker-compose.yml`.
- **Los schemas no aparecen en el DW:**
  Los scripts de `/docker-entrypoint-initdb.d/` solo se ejecutan cuando el volumen de base de datos está vacío. Si se crearon antes de montar el script, ejecute un reinicio limpio con `docker compose down -v` y vuelva a iniciar.
- **Variable requerida faltante:**
  Si falta alguna variable obligatoria en `.env`, `docker compose config` o `docker compose up` fallará indicando el nombre exacto de la variable que debe definirse.
