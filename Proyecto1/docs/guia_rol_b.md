# Guía de Arranque para Rol B (Transformación y Modelado)

Esta guía explica el estado actual del proyecto, la infraestructura disponible y las instrucciones paso a paso para que el **Rol B** comience el desarrollo del modelado dimensional con **dbt** sin fricciones ni dependencias bloqueantes con el **Rol A**.

---

## 1. Qué está hecho y disponible

El Rol A ha completado la infraestructura de ingesta y orquestación técnica del Proyecto 1:

1. **Entorno contenerizado:**
   - Docker Compose con PostgreSQL 16 para el Data Warehouse (`sgfood_dw`, expuesto en puerto host `5433`) y para la fuente transaccional (`sgfood_src`, expuesto en puerto host `5434`).
   - Apache Airflow 3.3.2 con `LocalExecutor`, API Server, Scheduler y DAG Processor saludables.
   - Entorno virtual aislado con **dbt Core 1.12.5** y adaptador **dbt-postgres 1.11.0** preinstalado en `/opt/dbt-venv` dentro de los contenedores de Airflow.
2. **Datos oficiales y contrato:**
   - La base transaccional (`oltp_sgfood`) se inicializa automáticamente con sus datos oficiales.
   - Los archivos CSV oficiales residen en `Proyecto1/data/`.
   - El contrato de datos está documentado en `Proyecto1/docs/contrato_raw.md` y codificado en `Proyecto1/python/config/fuentes.yml`.
3. **Carga y fidelidad en `raw`:**
   - El módulo `sgfood_ingesta` carga las 12 fuentes (7 tablas transaccionales y 5 archivos CSV) hacia el schema `raw` del DW, preservando tipos como texto y añadiendo la columna de auditoría `_loaded_at` compartida por ejecución.
   - Módulo de validación automática de conteos (fuente vs raw).
4. **Pipeline orquestado en Airflow (`sgfood_elt`):**
   - DAG completo de ejecución diaria y control de concurrencia (`max_active_runs=1`).
   - Secuencia del pipeline:
     1. Ingesta concurrente de las 12 tablas a `raw`.
     2. Validación automática de conteos (`validar_carga_raw`).
     3. Instalación de paquetes dbt (`dbt_deps`).
     4. Transformación de modelos dbt (`dbt_run`).
     5. Pruebas de calidad dbt (`dbt_test`).
     6. Validaciones SQL de negocio (`validar_marts`).
5. **Esqueleto de proyecto dbt:**
   - Inicializado en `Proyecto1/dbt_project/` con configuración lista para conectar a `sgfood_dw`.

---

## 2. Arranque en 5 pasos

### Paso 1: Clonar y verificar rama
Asegúrate de trabajar sobre tu rama de feature (por ejemplo, `feat/modelado-dbt`):
```bash
git checkout -b feat/modelado-dbt
```

### Paso 2: Configurar variables de entorno
Copia la plantilla `.env.example` a `.env` en la raíz de `Proyecto1/`:
```bash
cp Proyecto1/.env.example Proyecto1/.env
```
*(Verifica que las credenciales coincidan con las requeridas para desarrollo).*

### Paso 3: Levantar el entorno Docker
Desde la carpeta `Proyecto1/`:
```bash
docker compose up -d
```
Verifica que todos los servicios estén saludables (`healthy`):
```bash
docker compose ps
```

### Paso 4: Ejecutar el pipeline de ingesta inicial
Puedes disparar la carga completa a `raw` desde la línea de comandos o desde Airflow:
```bash
docker compose exec airflow-scheduler python -m sgfood_ingesta.cli
```
O disparando el DAG en Airflow:
```bash
docker compose exec airflow-scheduler airflow dags unpause -y sgfood_elt
docker compose exec airflow-scheduler airflow dags trigger sgfood_elt
```

### Paso 5: Probar dbt sobre el esqueleto
Verifica la conexión del proyecto dbt:
```bash
docker compose exec airflow-scheduler /opt/dbt-venv/bin/dbt debug --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
```

---

## 3. Cómo ejecutar dbt

### Opción A: Dentro del contenedor de Airflow (Recomendado)
No requiere instalar Python ni dbt en tu máquina host. La carpeta `Proyecto1/dbt_project/` está montada como volumen en `/opt/airflow/dbt_project`:

- **Compilar:**
  ```bash
  docker compose exec airflow-scheduler /opt/dbt-venv/bin/dbt compile --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
  ```
- **Ejecutar modelos:**
  ```bash
  docker compose exec airflow-scheduler /opt/dbt-venv/bin/dbt run --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
  ```
- **Ejecutar pruebas:**
  ```bash
  docker compose exec airflow-scheduler /opt/dbt-venv/bin/dbt test --project-dir /opt/airflow/dbt_project --profiles-dir /opt/airflow/dbt_project
  ```

### Opción B: Desde el equipo local (Host)
Si prefieres usar la CLI de dbt directamente en tu terminal:

1. Crea un virtualenv local e instala `dbt-postgres`:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   pip install dbt-postgres==1.11.0
   ```
2. Exporta las variables de entorno de conexión para apuntar al puerto publicado del DW (`5433`):
   ```bash
   export DW_HOST=localhost
   export DW_PORT=5433
   export DW_DB=sgfood_dw
   export DW_USER=dw_user
   export DW_PASSWORD=<tu_password_en_env>
   ```
3. Ejecuta comandos apuntando a `Proyecto1/dbt_project`:
   ```bash
   dbt run --project-dir Proyecto1/dbt_project --profiles-dir Proyecto1/dbt_project
   ```

---

## 4. Cómo agregar un modelo sin tocar nada del Rol A

El Rol B tiene autonomía total dentro de `Proyecto1/dbt_project/`:

1. **Crear modelos de Staging:**
   - Agrega archivos `.sql` dentro de `Proyecto1/dbt_project/models/staging/`.
   - Consume las fuentes de `raw` usando la macro `{{ source('oltp', 'tabla') }}` o `{{ source('archivos', 'tabla') }}` declaradas en `_fuentes.yml`.
   - Realiza el casteo de tipos desde `TEXT` (ej. `id_producto::int`, `fecha::date`, `monto::numeric(12,2)`).
2. **Crear modelos de Intermediate y Marts:**
   - Agrega modelos intermedios en `Proyecto1/dbt_project/models/intermediate/`.
   - Agrega dimensiones y tablas de hechos en `Proyecto1/dbt_project/models/marts/`.
   - Usa `{{ ref('nombre_modelo') }}` para referenciar modelos previos.
3. **Schemas automáticos:**
   - Gracias a la macro `macros/generate_schema_name.sql`, dbt escribe directamente en los schemas `staging` y `marts` del Data Warehouse sin prefijos redundantes.
4. **Integración automática en el pipeline:**
   - Cada vez que el DAG `sgfood_elt` se ejecute, correrá automáticamente `dbt run` y `dbt test` sobre todos tus modelos agregados. No necesitas modificar ningún archivo de Airflow, Python ni Docker.

---

## 5. Cómo agregar validaciones finales en `sql/validaciones/dag/`

Además de las pruebas de dbt (`dbt test`), el DAG cuenta con una tarea final (`validar_marts`) que corre consultas SQL de validación directa contra el DW:

1. **Ubicación:**
   - Coloca tus consultas en `Proyecto1/sql/validaciones/dag/`.
2. **Convención de nombres:**
   - Archivos con extensión `.sql` y prefijo numérico indicando orden de ejecución:
     `01_integridad_ventas_cliente.sql`, `02_balance_inventario.sql`.
3. **Criterio de aprobación:**
   - Cada consulta debe devolver **0 filas** si los datos son consistentes.
   - Cualquier fila devuelta representa una anomalía o inconsistencia y hará fallar la tarea `validar_marts`, deteniendo la finalización exitosa del DAG.
4. **Ejemplo (`01_ventas_sin_cliente.sql`):**
   ```sql
   -- Verifica que ninguna venta en el mart carezca de cliente dimensionado
   SELECT v.id_venta, v.id_cliente
   FROM marts.fct_ventas v
   LEFT JOIN marts.dim_cliente c ON v.id_cliente = c.id_cliente
   WHERE c.id_cliente IS NULL;
   ```

---

## 6. Matriz de responsabilidades y dependencias

| Componente / Ruta | Rol Responsable | Reglas de Colaboración |
|-------------------|-----------------|------------------------|
| `Proyecto1/data/` | Rol A | Archivos de datos inmutables byte a byte. No editar ni renombrar. |
| `Proyecto1/python/` | Rol A | Código de ingesta y conexiones. Rol B lo consume como servicio. |
| `Proyecto1/airflow/` | Rol A | Definición de DAGs y orquestación. Parámetros dinámicos vía `params`. |
| `Proyecto1/dbt_project/` | **Rol B** | Propiedad exclusiva de B tras la entrega del esqueleto. |
| `Proyecto1/sql/ddl/` | Compartido | DDL inicial de bases de datos. No alterar schemas base (`raw`, `staging`, `marts`). |
| `Proyecto1/sql/validaciones/dag/` | **Rol B** | Consultas finales de calidad de datos escritas por B. |
