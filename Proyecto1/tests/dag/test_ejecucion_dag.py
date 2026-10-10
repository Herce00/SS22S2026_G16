"""Pruebas de ejecución del DAG sgfood_elt."""
import json
import os
import time
import pytest
from conftest import run_docker_compose
from sgfood_ingesta.config import listar_fuentes


@pytest.mark.integracion
def test_ejecucion_tareas_carga_raw(proyecto1_dir):
    """Dispara el DAG sgfood_elt y verifica que las 12 tareas de carga terminen en success,

    que raw tenga 8864 filas y que todas las tablas compartan un único _loaded_at.
    """
    dag_id = "sgfood_elt"
    fuentes = listar_fuentes()
    run_id = None

    try:
        # 1. Despausar el DAG
        res_unpause = run_docker_compose(
            "exec", "-T", "airflow-scheduler", "airflow", "dags", "unpause", "-y", dag_id,
            cwd=proyecto1_dir
        )
        assert res_unpause.returncode == 0, f"Error al despausar {dag_id}: {res_unpause.stderr}"

        # 2. Preparar fixture dbt_ok en el contenedor scheduler
        import subprocess
        fixture_dbt = os.path.join(proyecto1_dir, "tests", "dag", "fixtures", "dbt_ok")
        run_docker_compose("exec", "-T", "airflow-scheduler", "mkdir", "-p", "/tmp/fixtures", cwd=proyecto1_dir)
        subprocess.run(["docker", "cp", fixture_dbt, "sgfood_airflow_scheduler:/tmp/fixtures/dbt_ok"], check=True)
        run_docker_compose("exec", "-T", "--user", "0", "airflow-scheduler", "chown", "-R", "airflow:root", "/tmp/fixtures", cwd=proyecto1_dir)

        # 3. Disparar el DAG con parámetros hacia dbt_ok
        conf_str = json.dumps({
            "dbt_project_dir": "/tmp/fixtures/dbt_ok",
            "dbt_profiles_dir": "/tmp/fixtures/dbt_ok",
        })
        res_trig = run_docker_compose(
            "exec", "-T", "airflow-scheduler", "airflow", "dags", "trigger", dag_id, "--conf", conf_str, "-o", "json",
            cwd=proyecto1_dir
        )
        assert res_trig.returncode == 0, f"Error al disparar {dag_id}: {res_trig.stderr}"
        lineas_trig = [l.strip() for l in res_trig.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
        if lineas_trig:
            try:
                trig_data = json.loads(lineas_trig[-1])
                if isinstance(trig_data, list) and len(trig_data) > 0:
                    run_id = trig_data[0].get("dag_run_id") or trig_data[0].get("run_id")
                elif isinstance(trig_data, dict):
                    run_id = trig_data.get("dag_run_id") or trig_data.get("run_id")
            except json.JSONDecodeError:
                pass

        assert run_id, f"No se pudo obtener el run_id del trigger:\n{res_trig.stdout}"

        # 4. Esperar que la ejecución termine (máx 120s)
        estado_final = None
        start_time = time.time()
        while time.time() - start_time < 120:
            res_runs = run_docker_compose(
                "exec", "-T", "airflow-scheduler", "airflow", "dags", "list-runs", dag_id, "-o", "json",
                cwd=proyecto1_dir
            )
            if res_runs.returncode == 0:
                lineas_runs = [l.strip() for l in res_runs.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
                if lineas_runs:
                    try:
                        runs = json.loads(lineas_runs[-1])
                        for r in runs:
                            curr_id = r.get("dag_run_id") or r.get("run_id")
                            if curr_id == run_id:
                                st = r.get("state")
                                if st in ["success", "failed"]:
                                    estado_final = st
                                    break
                        if estado_final:
                            break
                    except json.JSONDecodeError:
                        pass
            time.sleep(3)

        assert estado_final == "success", f"La ejecución del DAG terminó con estado '{estado_final}', se esperaba 'success'"

        # 5. Verificar que cada una de las 12 tareas de carga terminó en success
        res_tis = run_docker_compose(
            "exec", "-T", "airflow-scheduler", "airflow", "tasks", "states-for-dag-run", dag_id, run_id, "-o", "json",
            cwd=proyecto1_dir
        )
        lineas_tis = [l.strip() for l in res_tis.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
        assert len(lineas_tis) > 0, f"No se encontró JSON en states-for-dag-run:\n{res_tis.stdout}"
        tis_data = json.loads(lineas_tis[-1])
        estados_por_tarea = {ti.get("task_id"): ti.get("state") for ti in tis_data}

        for f in fuentes:
            t_id = f"carga_raw.cargar_{f.tabla_raw}"
            assert t_id in estados_por_tarea, f"Tarea {t_id} no encontrada en los task instances"
            assert estados_por_tarea[t_id] == "success", (
                f"Tarea {t_id} terminó con estado '{estados_por_tarea[t_id]}', se esperaba 'success'"
            )

        # T5: Verificar que validar_carga_raw terminó en success y registró el conteo
        assert "validar_carga_raw" in estados_por_tarea, "Tarea validar_carga_raw no encontrada"
        assert estados_por_tarea["validar_carga_raw"] == "success", (
            f"validar_carga_raw terminó con estado '{estados_por_tarea['validar_carga_raw']}', se esperaba 'success'"
        )

        # T6: Verificar tareas de dbt
        for dbt_task in ["dbt_deps", "dbt_run", "dbt_test"]:
            assert dbt_task in estados_por_tarea, f"Tarea {dbt_task} no encontrada en task instances"
            assert estados_por_tarea[dbt_task] == "success", (
                f"Tarea {dbt_task} terminó con estado '{estados_por_tarea[dbt_task]}', se esperaba 'success'"
            )

        # Buscar archivos de log de validar_carga_raw y dbt_run para este run
        logs_base = os.path.join(proyecto1_dir, "airflow", "logs", "dag_id=sgfood_elt")
        log_encontrado = False
        contenido_log = ""
        dbt_log_encontrado = False
        contenido_dbt_log = ""
        for root, dirs, files in os.walk(logs_base):
            if "task_id=validar_carga_raw" in root:
                for file in files:
                    if file.endswith(".log"):
                        with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as lf:
                            contenido_log += lf.read()
                        log_encontrado = True
            if "task_id=dbt_run" in root:
                for file in files:
                    if file.endswith(".log"):
                        with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as lf:
                            contenido_dbt_log += lf.read()
                        dbt_log_encontrado = True

        assert log_encontrado, f"No se encontró archivo de log para validar_carga_raw en {logs_base}"
        assert "8864" in contenido_log, f"El log de validar_carga_raw no contiene el total 8864:\n{contenido_log}"
        assert "12" in contenido_log, f"El log de validar_carga_raw no contiene el conteo de 12 tablas:\n{contenido_log}"

        assert dbt_log_encontrado, f"No se encontró archivo de log para dbt_run en {logs_base}"
        assert ("Running with dbt" in contenido_dbt_log or "Completed successfully" in contenido_dbt_log), (
            f"El log de dbt_run no contiene la salida esperada de dbt:\n{contenido_dbt_log}"
        )

        # 6. Verificar filas en raw (8864) y único _loaded_at
        script_dw = (
            "import psycopg\n"
            "from sgfood_ingesta.config import listar_fuentes\n"
            "from sgfood_ingesta.conexiones import conectar_dw\n"
            "fuentes = listar_fuentes()\n"
            "conn = conectar_dw()\n"
            "total_filas = 0\n"
            "todos_loaded_at = set()\n"
            "with conn.cursor() as cur:\n"
            "    for f in fuentes:\n"
            "        cur.execute(f'SELECT count(*), count(DISTINCT _loaded_at), min(_loaded_at) FROM raw.{f.tabla_raw}')\n"
            "        cnt, dist_loaded, sample_loaded = cur.fetchone()\n"
            "        total_filas += cnt\n"
            "        if cnt > 0:\n"
            "            todos_loaded_at.add(str(sample_loaded))\n"
            "conn.close()\n"
            "print(f'TOTAL={total_filas} LOADED_COUNT={len(todos_loaded_at)}')\n"
        )
        res_dw = run_docker_compose(
            "exec", "-T", "airflow-scheduler", "python", "-c", script_dw,
            cwd=proyecto1_dir
        )
        assert res_dw.returncode == 0, f"Error al verificar DW:\n{res_dw.stdout}\n{res_dw.stderr}"
        assert "TOTAL=8864" in res_dw.stdout, f"Se esperaban 8864 filas en raw:\n{res_dw.stdout}"
        assert "LOADED_COUNT=1" in res_dw.stdout, f"Todas las tablas deben compartir un único _loaded_at:\n{res_dw.stdout}"

        # 7. T6: Verificar que el modelo del proyecto de prueba existe en schema dag_test con 6 filas
        res_dbt_check = run_docker_compose(
            "exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-tAc",
            "SELECT count(*) FROM dag_test.test_sucursal;",
            cwd=proyecto1_dir
        )
        assert res_dbt_check.returncode == 0, f"Error al consultar dag_test en DW:\n{res_dbt_check.stderr}"
        assert res_dbt_check.stdout.strip() == "6", f"Se esperaban 6 filas en dag_test.test_sucursal:\n{res_dbt_check.stdout}"

    finally:
        # Limpieza: eliminar schema de prueba en DW y pausar el DAG
        run_docker_compose(
            "exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c",
            "DROP SCHEMA IF EXISTS dag_test CASCADE;",
            cwd=proyecto1_dir
        )
        run_docker_compose(
            "exec", "-T", "airflow-scheduler", "airflow", "dags", "pause", "-y", dag_id,
            cwd=proyecto1_dir
        )
