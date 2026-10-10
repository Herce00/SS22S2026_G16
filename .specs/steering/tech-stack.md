# Stack tecnológico — Proyecto 1 (SG-Food)

Las cuatro tecnologías obligatorias son Python, Apache Airflow, dbt Core y PostgreSQL. Cualquier herramienta fuera de este documento necesita justificación y acuerdo de la pareja.

Es válido para los dos integrantes. Los roles A y B están definidos en [architecture.md](architecture.md).

- **Fuente de requisitos:** [Proyecto1/enunciado.md](../../Proyecto1/enunciado.md), sección 3.3
- **Documentos hermanos:** [architecture.md](architecture.md) · [coding-standards.md](coding-standards.md)

## Componentes obligatorios

| Componente | Uso en el proyecto | Dueño |
|------------|-------------------|-------|
| Python 3.x | Extracción, carga a `raw` y scripts auxiliares | A |
| Apache Airflow | Orquestación: carga, `dbt run`, `dbt test`, validaciones | A |
| PostgreSQL | Data Warehouse con schemas `raw`, `staging`, `marts` | A (infraestructura y `raw`) / B (`staging` y `marts`) |
| dbt Core + `dbt-postgres` | Modelos staging, intermediate y marts; pruebas y documentación | B |
| BD transaccional | Fuente de datos número 1 | A |
| Archivos CSV o delimitados | Fuente de datos número 2, cargada con Python | A |

## Componentes acordados

No los exige el enunciado; son decisiones de la pareja (ver "Decisiones acordadas" en [architecture.md](architecture.md)).

| Componente | Decisión | Dueño | Motivo |
|------------|----------|-------|--------|
| Docker Compose | Levanta DW, BD fuente y Airflow | A | Reproducibilidad y manual de implementación corto |
| Motor de la BD fuente | PostgreSQL en contenedor separado del DW | A | Un solo motor y un solo driver |
| Driver de base de datos | `psycopg` | A | Soporta `COPY` para carga masiva |
| Lectura de CSV | Biblioteca estándar (`csv`) | A | Lectura directa en streaming sin dependencias pesadas; `pandas` retirado |
| Ejecución de dbt desde Airflow | `BashOperator` con `dbt run` y `dbt test` | A implementa, B define los comandos | Sin dependencias adicionales |
| Configuración | Archivo `.env` + conexiones y variables de Airflow | Ambos | Cubre el punto opcional de parametrización |
| Conexión de dbt | `profiles.yml` que lee las mismas variables de entorno | B | Una sola fuente de configuración |

## Componentes opcionales

Solo si el alcance obligatorio está completo.

| Componente | Uso | Dueño |
|------------|-----|-------|
| Power BI, Metabase o Superset | Visualización sobre `marts` | B, con apoyo de A |
| Programación del DAG | Ejecución periódica | A |

## Versiones

Las versiones exactas están **fijadas y verificadas** contra la documentación oficial.

| Componente | Versión | Estado |
|------------|---------|--------|
| Python | 3.12 | Fijada |
| Apache Airflow | 3.3.2 (`apache/airflow:3.3.2-python3.12`) | Fijada |
| PostgreSQL | 16 (`postgres:16`) | Fijada |
| dbt Core / `dbt-postgres` | `dbt-core==1.12.5` / `dbt-postgres==1.11.0` | Fijada |

Reglas para fijarlas:

1. Verificar la compatibilidad entre Airflow, Python y dbt en la documentación oficial antes de elegir; no fijar versiones de memoria.
2. Fijar versiones exactas en las imágenes de Docker y en `requirements.txt`; no usar `latest`.
3. Instalar dbt aislado de las dependencias de Airflow si aparecen conflictos entre paquetes.
4. Ambos integrantes desarrollan contra el mismo entorno de Docker, no contra instalaciones locales distintas.
5. Cambiar una versión ya fijada es zona amarilla: afecta el trabajo de los dos.

## Restricciones

- No se usa SQL Server; eso pertenece a las Prácticas 1 y 2.
- No se agregan orquestadores, motores de base de datos ni frameworks de transformación alternativos.
- Las transformaciones de negocio no se escriben en Python ni en SQL suelto: van en dbt.
- No se suben al repositorio credenciales, archivos `.env` reales, ni carpetas generadas (`target/`, `dbt_packages/`, `logs/`).

## Material de referencia

- Apache Airflow: <https://airflow.apache.org/docs/>
- dbt: <https://docs.getdbt.com/>
- PostgreSQL: <https://www.postgresql.org/docs/>
- dbt para PostgreSQL: <https://docs.getdbt.com/docs/core/connect-data-platform/postgres-setup>
