import json
import os
import shutil
import time
import pytest
from conftest import run_docker_compose

@pytest.mark.integracion
def test_ejecucion_tarea_smoke_dag(proyecto1_dir):
    """Verifica que el scheduler real ejecute una tarea (smoke DAG con SELECT 1 en dw) y termine en 'success'."""
    src_dag = os.path.join(proyecto1_dir, "tests", "entorno", "dags", "smoke_dag.py")
    dest_dag = os.path.join(proyecto1_dir, "airflow", "dags", "smoke_dag.py")

    assert os.path.exists(src_dag), f"No existe el archivo {src_dag}"

    # Copiar el DAG de humo a la carpeta monitoreada por Airflow
    shutil.copyfile(src_dag, dest_dag)

    dag_id = "smoke_test_task_execution"
    try:
        # Forzar reserialización para procesar el archivo inmediatamente
        run_docker_compose("exec", "-T", "airflow-dag-processor", "airflow", "dags", "reserialize", cwd=proyecto1_dir)

        # Esperar a que aparezca en airflow dags list
        dag_registrado = False
        start_wait = time.time()
        while time.time() - start_wait < 30:
            res_list = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list", "-o", "json", cwd=proyecto1_dir)
            if res_list.returncode == 0 and dag_id in res_list.stdout:
                dag_registrado = True
                break
            time.sleep(2)

        assert dag_registrado, f"El DAG {dag_id} no fue registrado por Airflow dentro de 30s:\n{res_list.stdout} {res_list.stderr}"

        # Despausar el DAG explícitamente para permitir la ejecución de sus tareas
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "unpause", "-y", dag_id, cwd=proyecto1_dir)

        # Disparar el DAG a través del scheduler
        res_trigger = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "trigger", dag_id, "-o", "json", cwd=proyecto1_dir)
        assert res_trigger.returncode == 0, f"Fallo al disparar DAG {dag_id}:\n{res_trigger.stderr}"

        # Esperar a que la ejecución termine en 'success'
        ejecucion_terminada = False
        estado_final = None
        start_exec = time.time()
        while time.time() - start_exec < 90:
            res_runs = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list-runs", dag_id, "-o", "json", cwd=proyecto1_dir)
            if res_runs.returncode == 0:
                try:
                    runs_data = json.loads(res_runs.stdout)
                    if isinstance(runs_data, list) and len(runs_data) > 0:
                        estado_final = runs_data[0].get("state")
                        if estado_final in ["success", "failed"]:
                            ejecucion_terminada = True
                            break
                except json.JSONDecodeError:
                    pass
            time.sleep(3)

        assert ejecucion_terminada, f"La ejecución del DAG no terminó en el tiempo esperado (estado: {estado_final})"
        assert estado_final == "success", f"La ejecución del DAG terminó con estado '{estado_final}', se esperaba 'success'"

    finally:
        # Limpieza: eliminar el DAG copiado y borrar el registro en Airflow para que no quede cargado
        if os.path.exists(dest_dag):
            os.remove(dest_dag)
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "delete", "-y", dag_id, cwd=proyecto1_dir)

    # Verificar que el DAG de humo no quede en la lista de DAGs fuera de la prueba y que sgfood_elt permanezca
    res_final_list = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list", "-o", "json", cwd=proyecto1_dir)
    assert res_final_list.returncode == 0
    assert dag_id not in res_final_list.stdout, f"El DAG {dag_id} no debe quedar cargado fuera de la prueba"
    assert "sgfood_elt" in res_final_list.stdout, "El DAG sgfood_elt debe permanecer en Airflow"

