import os
from datetime import datetime, timedelta, timezone

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param, TaskGroup, task

from sgfood_ingesta.config import listar_fuentes
from sgfood_ingesta.ingesta import cargar_fuente
from sgfood_ingesta.validacion import validar_conteos

# Configuración y argumentos por defecto
DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=10),
}


with DAG(
    dag_id="sgfood_elt",
    description="Pipeline ELT de ingesta, transformación y validación de SG-Food",
    schedule="@daily",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=4,
    is_paused_upon_creation=True,
    tags=["sgfood", "elt"],
    default_args=DEFAULT_ARGS,
    params={
        "dbt_project_dir": Param(
            default=os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt_project"),
            type="string",
            description="Ruta del proyecto dbt a ejecutar",
        ),
        "dbt_profiles_dir": Param(
            default=os.environ.get("DBT_PROFILES_DIR", "/opt/airflow/dbt_project"),
            type="string",
            description="Ruta de la carpeta profiles.yml de dbt",
        ),
        "validaciones_dir": Param(
            default="/opt/airflow/sql/validaciones/dag",
            type="string",
            description="Ruta de la carpeta de validaciones SQL finales",
        ),
    },
) as dag:

    # 1. Grupo de tareas dinámicas de ingesta a raw
    with TaskGroup(group_id="carga_raw") as carga_raw:
        fuentes = listar_fuentes()

        def crear_tarea_carga(tabla: str):
            @task(
                task_id=f"cargar_{tabla}",
                retries=2,
                retry_delay=timedelta(minutes=1),
                execution_timeout=timedelta(minutes=10),
            )
            def tarea_carga(**context):
                dag_run = context.get("dag_run")
                loaded_at = getattr(dag_run, "start_date", None) or context.get("logical_date")
                cargar_fuente(tabla, loaded_at=loaded_at)

            return tarea_carga()

        for f in fuentes:
            crear_tarea_carga(f.tabla_raw)

    # 2. Validación de la carga a raw (compara conteos fuente vs raw)
    @task(
        task_id="validar_carga_raw",
        retries=0,
        execution_timeout=timedelta(minutes=5),
    )
    def validar_carga_raw():
        validar_conteos()

    t_validar_carga_raw = validar_carga_raw()

    # 3. Tareas dbt (deps, run, test)
    dbt_env = {
        "DBT_PROJECT_DIR": "{{ params.dbt_project_dir }}",
        "DBT_PROFILES_DIR": "{{ params.dbt_profiles_dir }}",
    }

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=(
            'if [ -f "$DBT_PROJECT_DIR/packages.yml" ]; then '
            '/opt/dbt-venv/bin/dbt deps --project-dir "$DBT_PROJECT_DIR" --profiles-dir "$DBT_PROFILES_DIR"; '
            'else echo "packages.yml no existe; omitiendo dbt deps"; fi'
        ),
        env=dbt_env,
        append_env=True,
        retries=2,
        retry_delay=timedelta(minutes=1),
        execution_timeout=timedelta(minutes=10),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command='/opt/dbt-venv/bin/dbt run --project-dir "$DBT_PROJECT_DIR" --profiles-dir "$DBT_PROFILES_DIR"',
        env=dbt_env,
        append_env=True,
        retries=1,
        retry_delay=timedelta(minutes=1),
        execution_timeout=timedelta(minutes=20),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command='/opt/dbt-venv/bin/dbt test --project-dir "$DBT_PROJECT_DIR" --profiles-dir "$DBT_PROFILES_DIR"',
        env=dbt_env,
        append_env=True,
        retries=0,
        execution_timeout=timedelta(minutes=20),
    )

    # 4. Validación final de marts
    @task(task_id="validar_marts", retries=0, execution_timeout=timedelta(minutes=10))
    def validar_marts(**context) -> None:
        from sgfood_ingesta.validacion import validar_sql
        params = context.get("params") or {}
        carpeta = params.get("validaciones_dir", "/opt/airflow/sql/validaciones/dag")
        validar_sql(carpeta=str(carpeta))

    t_validar_marts = validar_marts()

    # Dependencias del pipeline ELT
    carga_raw >> t_validar_carga_raw >> dbt_deps >> dbt_run >> dbt_test >> t_validar_marts


