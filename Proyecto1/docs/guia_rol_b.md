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

### Paso 1: Crear tu rama desde `main`

El trabajo del Rol A llega a `main` por pull request. Crea tu rama **después** de ese merge; si la creas antes, no tendrás el entorno, los datos ni el esqueleto.

```bash
git checkout main
git pull
git checkout -b feat/dbt-modelado
```

El nombre `feat/dbt-modelado` es el acordado en el steering. Cada integrante trabaja solo en su rama y los cambios entran a `main` por pull request revisado por el otro.

### Paso 2: Configurar variables de entorno

Copia la plantilla `.env.example` a `.env` en la raíz de `Proyecto1/`:

```bash
cp Proyecto1/.env.example Proyecto1/.env
```

_(Verifica que las credenciales coincidan con las requeridas para desarrollo)._

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
docker compose exec airflow-scheduler python -m sgfood_ingesta
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
   - Convierte los tipos desde `TEXT`. Hazlo de forma tolerante: un `::int` directo detiene el modelo ante un solo valor inválido. El modelo de ejemplo muestra el patrón: `CASE WHEN id_producto ~ '^[0-9]+$' THEN id_producto::int END`, y una prueba `not_null` reporta lo que no se pudo convertir.
   - El tipo esperado de cada columna está en `Proyecto1/docs/contrato_raw.md`.
2. **Crear modelos de Intermediate y Marts:**
   - Agrega modelos intermedios en `Proyecto1/dbt_project/models/intermediate/`.
   - Agrega dimensiones y tablas de hechos en `Proyecto1/dbt_project/models/marts/`.
   - Usa `{{ ref('nombre_modelo') }}` para referenciar modelos previos.
3. **Schemas automáticos:**
   - Gracias a la macro `macros/generate_schema_name.sql`, dbt escribe directamente en los schemas `staging` y `marts` del Data Warehouse sin prefijos redundantes.
   - **`intermediate` no tiene schema asignado.** Tal como está, un modelo en esa carpeta se crea en `public`. Dónde vive esa capa es decisión tuya: agrega `+schema: staging`, u otro nombre, bajo `intermediate` en `dbt_project.yml`.
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

| Componente / Ruta                | Rol Responsable | Reglas de Colaboración                                                                         |
| -------------------------------- | --------------- | ---------------------------------------------------------------------------------------------- |
| `Proyecto1/data/`                | Rol A           | Archivos de datos inmutables byte a byte. No editar ni renombrar.                              |
| `Proyecto1/python/`              | Rol A           | Código de ingesta y conexiones. Rol B lo consume como servicio.                                |
| `Proyecto1/airflow/`             | Rol A           | Definición de DAGs y orquestación. Parámetros dinámicos vía `params`.                          |
| `Proyecto1/dbt_project/`         | **Rol B**       | Propiedad exclusiva de B tras la entrega del esqueleto.                                        |
| `Proyecto1/sql/ddl/`             | Rol A           | DDL de schemas y tablas de `raw`. Las tablas de `staging` y `marts` las crea dbt, no este DDL. |
| `Proyecto1/sql/validaciones/`    | **Rol B**       | Consultas analíticas y de validación. La subcarpeta `dag/` es la que ejecuta el DAG.           |
| `Proyecto1/docs/contrato_raw.md` | Compartido      | Interfaz entre los dos roles. Se cambia solo con acuerdo.                                      |
| `Proyecto1/tests/`               | Rol A           | Pruebas de entorno, contrato, ingesta y DAG. No dependen del contenido de `dbt_project/`.      |

### Qué puedes cambiar sin avisar

Modelos, capas, nombres de modelos, materializaciones, diseño dimensional, pruebas dbt, macros, paquetes, documentación, el schema de `intermediate`, los archivos de `sql/validaciones/` y el uso de los casos de calidad opcionales. Nada de eso afecta al Rol A: el DAG ejecuta el proyecto completo sin conocer su contenido.

### Qué necesita acuerdo con el Rol A

- Cambiar tablas o columnas de `raw`, o pedir columnas de auditoría nuevas.
- Renombrar los schemas `raw`, `staging` o `marts`, o las variables `DW_*`.
- Necesitar argumentos distintos de dbt en el DAG: selectores, variables u objetivos.
- Mover `profiles.yml` o el proyecto dbt a otra ruta.
- Cambiar la convención de las validaciones finales.
- Agregar dependencias Python o cambiar versiones fijadas.

El detalle está en la sección "Interfaz entre A y B" de `.specs/steering/architecture.md`.

---

## 7. Qué te queda por hacer

Lo que sigue es el alcance del Rol B según el enunciado y la rúbrica. El esqueleto solo resuelve la parte mecánica.

### Obligatorio

- [x] **Diseñar el modelo dimensional.** Definir hechos, dimensiones y granularidad. Los datos dan para, al menos, ventas (al nivel de línea de detalle) e inventario (foto mensual), con dimensiones como producto, marca, categoría, cliente, sucursal y tiempo. Devoluciones, metas, promociones y precios de proveedores pueden ser hechos o dimensiones adicionales.
- [x] **Modelos `staging`** para las 11 tablas restantes de `raw`: renombrar, convertir tipos y limpiar. Sin joins.
- [x] **Modelos `intermediate`** con los joins y la lógica reutilizable, y decidir en qué schema viven.
- [x] **Modelos `marts`**: dimensiones y hechos, con sus claves y relaciones.
- [x] **Materializaciones** coherentes por capa, con al menos una `incremental` donde tenga sentido.
- [x] **Pruebas dbt**: `unique` y `not_null` en cada clave, `relationships` de hechos a dimensiones, `accepted_values` en columnas categóricas y al menos una prueba personalizada.
- [x] **Documentación dbt**: descripciones en YAML y `dbt docs generate` sin errores.
- [x] **Consultas analíticas y de validación** en `sql/validaciones/`: conteos, integridad referencial y resultados de negocio. Las que deban detener el pipeline van en `sql/validaciones/dag/`.
- [x] **Secciones del README** que hoy están marcadas como pendientes: modelo del Data Warehouse, estructura del proyecto dbt y justificación de diseño.
- [x] **Evidencia** de tu parte en `Proyecto1/evidencia/`: actualizar los resultados de `dbt run`, `dbt test` y de las consultas analíticas para que correspondan a los modelos actuales.

### Decisiones abiertas que son tuyas

- [x] En qué schema se materializa `intermediate`.
- [x] Si se usan los casos de `casos_calidad_opcionales.csv` y cómo. No se cargan en la corrida principal (decisión D8).
- [x] Conservar, modificar o eliminar el modelo de ejemplo `stg_oltp__sucursal`.

### Opcional

- [ ] Conectar los `marts` a Power BI, Metabase o Superset.

### Cómo saber que terminaste

Dispara `sgfood_elt` desde Airflow. Si las 17 tareas terminan en verde con tus modelos, tus pruebas y tus validaciones, el pipeline completo está integrado. No hace falta que el Rol A cambie nada.
