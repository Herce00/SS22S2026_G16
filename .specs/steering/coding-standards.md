# Convenciones de código — Proyecto 1 (SG-Food)

Convenciones base para todo el código del proyecto: colaboración, nombres, Python, SQL, Airflow y dbt. Es válido para los dos integrantes; cada sección indica a qué rol aplica.

Los roles A y B y los límites de cada uno están en [architecture.md](architecture.md).

- **Documentos hermanos:** [architecture.md](architecture.md) · [tech-stack.md](tech-stack.md)

| Sección | Aplica a |
|---------|----------|
| Estructura, Git, nombres, documentación | Ambos |
| Python, SQL de `raw`, Airflow | A |
| dbt, SQL de validación | B |

## Estructura del repositorio

```
Proyecto1/
├── README.md
├── docker-compose.yml
├── .env.example
├── docs/           contrato_raw.md
├── sql/
│   ├── ddl/            schemas y tablas raw            (A)
│   └── validaciones/   validaciones y consultas        (B)
├── python/         extracción, carga y configuración   (A)
├── airflow/dags/                                       (A)
├── dbt_project/    models/staging, intermediate, marts (B)
└── evidencia/
```

Cambiar esta estructura requiere acuerdo de ambos.

## Git y colaboración

| Regla | Detalle |
|-------|---------|
| Ramas | `feat/ingesta-airflow` (A) y `feat/dbt-modelado` (B), creadas desde `main` |
| Integración | Pull request cruzado: cada uno revisa el del otro antes del merge a `main` |
| Commits | Conventional Commits con alcance: `feat(p1-ingesta): ...`, `feat(p1-dbt): ...`, `fix(p1-airflow): ...`, `docs(p1): ...` |
| Autoría | Cada integrante hace commit de su propio trabajo; sin atribuciones automáticas de herramientas |
| Tamaño | Un commit por unidad de trabajo coherente, con su documentación |
| Prohibido | Push directo a `main`, push a la rama del otro, `--force` sobre ramas compartidas |

Los commits de ambos integrantes son la evidencia del trabajo en pareja que pide la rúbrica.

## Nombres

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Schemas | minúsculas, fijos | `raw`, `staging`, `marts` |
| Tablas y columnas | `snake_case`, minúsculas, sin acentos ni espacios | `raw.ventas` |
| Columnas de auditoría en `raw` | prefijo `_` | `_loaded_at`, `_source` |
| Modelos dbt staging | `stg_<fuente>__<entidad>` | `stg_transaccional__ventas` |
| Modelos dbt intermediate | `int_<entidad>_<acción>` | `int_ventas_enriquecidas` |
| Dimensiones y hechos | `dim_<entidad>`, `fct_<proceso>` | `dim_producto`, `fct_ventas` |
| Claves sustitutas | `<entidad>_key` | `producto_key` |
| Módulos y funciones Python | `snake_case` | `extract_transaccional.py` |
| DAG | `snake_case` descriptivo | `sgfood_elt` |
| Tareas del DAG | verbo + objeto | `load_csv_productos`, `dbt_run`, `validate_counts` |
| Variables de entorno | mayúsculas con prefijo por servicio | `DW_HOST`, `SRC_HOST` |

Los nombres de entidades provienen de los datos oficiales (ver [architecture.md](architecture.md)). Los nombres de tablas y columnas de `raw` forman parte del contrato: no se renombran sin acuerdo.

## Python (rol A)

- Un módulo por responsabilidad: extracción, carga y utilidades de conexión separados.
- La lista de fuentes y sus tablas destino vive en un archivo de configuración, no en el código.
- Funciones pequeñas con anotaciones de tipo y un `docstring` breve.
- Configuración solo desde variables de entorno; ninguna credencial, host o ruta absoluta en el código.
- Registro con el módulo `logging`, no con `print`. Cada carga registra fuente, tabla destino y filas procesadas.
- Los errores no se silencian: se registran y se relanzan para que Airflow marque la tarea como fallida.
- Carga por truncado y recarga dentro de una transacción; reejecutar no duplica filas.
- Los valores se cargan como texto, sin conversión de tipos.
- Consultas parametrizadas; nunca concatenar valores dentro del SQL.
- Sin lógica de negocio: solo limpieza técnica mínima (regla 2 de [architecture.md](architecture.md)).
- Cada script debe poder ejecutarse fuera de Airflow para depurarlo.

## SQL de `raw` (rol A)

- Palabras clave en mayúsculas, identificadores en minúsculas.
- Scripts reejecutables: `CREATE SCHEMA IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`.
- El DDL crea los tres schemas y las tablas de `raw`. Las tablas de `staging` y `marts` las crea dbt.
- Columnas de negocio como `TEXT`; solo las columnas de auditoría tienen tipo propio.
- Sin claves primarias, foráneas ni restricciones de negocio en `raw`; la integridad se valida con pruebas dbt.
- Cada tabla lleva un comentario con su fuente de origen.

## Airflow (rol A)

- Un DAG principal con el flujo completo: carga → `dbt run` → `dbt test` → validaciones.
- `default_args` con reintentos y espera entre reintentos definidos de forma explícita.
- Sin lógica pesada a nivel de módulo del DAG: el archivo debe importarse rápido.
- Las tareas llaman a funciones de `python/`; no se duplica código dentro del DAG.
- dbt se invoca con `BashOperator`; los comandos y selectores los define B.
- Conexiones y variables desde Airflow o desde el entorno, nunca escritas en el DAG.
- Dependencias declaradas de forma explícita; una tarea fallida detiene las posteriores.
- Si se programa el DAG, usar `catchup=False` salvo acuerdo en contrario.

## dbt (rol B)

- `sources.yml` declara el schema `raw` y respeta el contrato raw.
- Todo acceso a `raw` usa `source()`; todo acceso entre modelos usa `ref()`.
- Tres capas en carpetas separadas: `staging`, `intermediate`, `marts`.

| Capa | Responsabilidad | Materialización base |
|------|----------------|---------------------|
| Staging | Un modelo por tabla de `raw`: renombrar, convertir tipos desde `TEXT`, limpiar. Sin joins. | `view` |
| Intermediate | Joins y lógica de negocio reutilizable | `view` o `ephemeral` |
| Marts | Dimensiones y hechos del esquema estrella | `table`; `incremental` donde aplique |

- La conversión de tipos se hace solo en `staging` y debe tolerar valores inválidos sin romper el modelo.
- Las columnas de auditoría de `raw` no se propagan a `marts` salvo que tengan uso analítico.
- Pruebas mínimas: `unique` y `not_null` en cada clave, `relationships` de hechos a dimensiones, `accepted_values` en columnas categóricas y al menos una prueba personalizada.
- Cada modelo y cada columna de `marts` tiene descripción en YAML; `dbt docs generate` debe ejecutarse sin errores.
- `profiles.yml` lee la conexión desde variables de entorno; no se suben credenciales.
- No se suben `target/`, `dbt_packages/` ni `logs/`.

B puede ajustar las convenciones internas de dbt; un cambio que afecte al DAG o al contrato raw es zona amarilla.

## SQL de validación y consultas analíticas (rol B)

- Un archivo por propósito: conteos, integridad referencial, resultados de negocio.
- Cada consulta lleva un comentario con la pregunta que responde y el resultado esperado.
- Las consultas leen de `marts`; las de conteo pueden comparar `raw` contra `marts`.
- Las consultas que usa la tarea de validación del DAG se acuerdan con A.

## Documentación y evidencia

- Documentación del proyecto en español, tono técnico y neutro.
- Cada sección del README tiene un dueño (mapa de propiedad en [architecture.md](architecture.md)); el otro integrante la revisa.
- La evidencia va en `Proyecto1/evidencia/` con nombres descriptivos: `dag_ejecucion_exitosa.png`, `dbt_test_resultado.png`.
- No se inventan cifras: todo conteo o resultado citado debe provenir de una ejecución real sobre los datos oficiales de `Proyecto1/data/`.
- Los archivos de `Proyecto1/data/` se versionan tal como los entregó el curso y no se editan a mano.
- Los CSV se leen como `utf-8-sig` porque incluyen BOM.

## Antes de abrir un pull request

Ambos:

- [ ] El cambio está en zona verde del rol propio, o el cambio de zona amarilla fue acordado.
- [ ] No hay credenciales ni archivos generados en el commit.
- [ ] El README y la evidencia de la parte afectada están actualizados.

Rol A:

- [ ] `docker compose up` levanta el entorno desde cero.
- [ ] El DAG se importa sin errores y la ejecución completa termina correctamente.
- [ ] Reejecutar la carga no duplica filas en `raw`.

Rol B:

- [ ] `dbt run` y `dbt test` terminan sin errores dentro del entorno de Docker.
- [ ] Ningún modelo referencia tablas por nombre directo.
- [ ] `dbt docs generate` se ejecuta sin errores.
