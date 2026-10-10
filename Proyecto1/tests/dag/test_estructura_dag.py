"""Pruebas de estructura, configuración y análisis estático del DAG sgfood_elt (T4)."""
import json
import os
import pytest
from conftest import run_docker_compose
from sgfood_ingesta.config import listar_fuentes


def test_archivo_dag_sin_nombres_tablas_sql_ni_credenciales(proyecto1_dir):
    """El archivo del DAG no debe contener nombres de tablas literales, sentencias SQL ni credenciales."""
    dag_path = os.path.join(proyecto1_dir, "airflow", "dags", "sgfood_elt.py")
    assert os.path.isfile(dag_path), f"El archivo del DAG no existe: {dag_path}"

    with open(dag_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    # 1. No debe contener nombres de tablas escritos como literales
    fuentes = listar_fuentes()
    for f in fuentes:
        # Verificar que no aparezca el nombre entre comillas ("tabla" o 'tabla')
        assert f"'{f.tabla_raw}'" not in contenido, (
            f"El archivo del DAG contiene el nombre de tabla literal '{f.tabla_raw}'"
        )
        assert f'"{f.tabla_raw}"' not in contenido, (
            f'El archivo del DAG contiene el nombre de tabla literal "{f.tabla_raw}"'
        )

    # 2. No debe contener SQL
    palabras_sql = ["SELECT ", "INSERT ", "TRUNCATE ", "DELETE ", "COPY ", "UPDATE "]
    contenido_upper = contenido.upper()
    for sql_word in palabras_sql:
        assert sql_word not in contenido_upper, (
            f"El archivo del DAG contiene SQL prohibido: '{sql_word}'"
        )

    # 3. No debe contener credenciales hardcodeadas
    for cred in ["password", "cambiar_dw_pass", "cambiar_src_pass", "cambiar_admin_pass"]:
        assert cred not in contenido.lower(), (
            f"El archivo del DAG contiene posible credencial hardcodeada: '{cred}'"
        )


@pytest.mark.integracion
def test_estructura_y_configuracion_dag(proyecto1_dir):
    """Verifica en Airflow que sgfood_elt se importe sin errores y tenga la configuración y tareas esperadas."""
    # 1. Verificar que no haya errores de importación en Airflow
    res_err = run_docker_compose(
        "exec", "-T", "airflow-scheduler", "airflow", "dags", "list-import-errors", "-o", "json",
        cwd=proyecto1_dir
    )
    assert res_err.returncode == 0, f"Error al consultar list-import-errors: {res_err.stderr}"
    try:
        import_errors = json.loads(res_err.stdout)
        # Asegurar que no hay errores para sgfood_elt.py
        for err in import_errors:
            assert "sgfood_elt" not in str(err), f"Error de importación detectado en sgfood_elt: {err}"
    except json.JSONDecodeError:
        pass

    # 2. Inspeccionar el objeto DAG y sus tareas mediante script en el contenedor
    script_check = (
        "import json\n"
        "from datetime import timedelta\n"
        "try:\n"
        "    from airflow.dag_processing.dagbag import DagBag\n"
        "except ImportError:\n"
        "    from airflow.models.dagbag import DagBag\n"
        "from sgfood_ingesta.config import listar_fuentes\n"
        "bag = DagBag(dag_folder='/opt/airflow/dags')\n"
        "if 'sgfood_elt' not in bag.dags:\n"
        "    print(json.dumps({'error': 'DAG sgfood_elt no encontrado en DagBag'}))\n"
        "    exit(1)\n"
        "dag = bag.dags['sgfood_elt']\n"
        "fuentes = listar_fuentes()\n"
        "tareas_esperadas = [f'carga_raw.cargar_{f.tabla_raw}' for f in fuentes]\n"
        "tareas_reintentos_ok = all(\n"
        "    dag.get_task(t).retries == 2 and dag.get_task(t).execution_timeout == timedelta(minutes=10)\n"
        "    for t in tareas_esperadas if t in dag.task_dict\n"
        ")\n"
        "info = {\n"
        "    'dag_id': dag.dag_id,\n"
        "    'is_paused': dag.is_paused_upon_creation,\n"
        "    'schedule': str(dag.schedule_interval if hasattr(dag, 'schedule_interval') and dag.schedule_interval else dag.schedule),\n"
        "    'catchup': dag.catchup,\n"
        "    'max_active_runs': dag.max_active_runs,\n"
        "    'max_active_tasks': dag.max_active_tasks,\n"
        "    'task_ids': list(dag.task_dict.keys()),\n"
        "    'tareas_esperadas': tareas_esperadas,\n"
        "    'tareas_reintentos_ok': tareas_reintentos_ok,\n"
        "}\n"
        "print(json.dumps(info))\n"
    )

    res_info = run_docker_compose(
        "exec", "-T", "airflow-scheduler", "python", "-c", script_check,
        cwd=proyecto1_dir
    )
    assert res_info.returncode == 0, f"Error al inspeccionar DAG en el contenedor:\n{res_info.stdout}\n{res_info.stderr}"

    # Buscar la línea JSON válida ignorando los logs de Airflow
    lineas_json = [l.strip() for l in res_info.stdout.splitlines() if l.strip().startswith("{") and l.strip().endswith("}")]
    assert len(lineas_json) > 0, f"No se encontró salida JSON en:\n{res_info.stdout}"
    data = json.loads(lineas_json[-1])

    assert data["dag_id"] == "sgfood_elt"
    assert data["is_paused"] is True, "El DAG debe crearse en pausa (is_paused_upon_creation=True)"
    assert data["schedule"] in ["@daily", "0 0 * * *"], f"Programación debe ser diaria, obtenido: {data['schedule']}"
    assert data["catchup"] is False, "catchup debe ser False"
    assert data["max_active_runs"] == 1, "max_active_runs debe ser 1"
    assert data["max_active_tasks"] == 4, "max_active_tasks debe ser 4"

    # Verificar tareas de carga
    tareas_esperadas = data["tareas_esperadas"]
    for t_id in tareas_esperadas:
        assert t_id in data["task_ids"], f"Tarea de carga '{t_id}' no encontrada en el DAG"
    assert data["tareas_reintentos_ok"] is True, "Las tareas de carga deben tener 2 reintentos y 10m de tiempo límite"
