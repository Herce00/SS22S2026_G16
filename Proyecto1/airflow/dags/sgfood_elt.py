"""DAG de orquestación técnica ELT para SG-Food."""
from datetime import datetime, timedelta, timezone

from airflow.sdk import DAG, TaskGroup, task

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
    carga_raw >> t_validar_carga_raw

