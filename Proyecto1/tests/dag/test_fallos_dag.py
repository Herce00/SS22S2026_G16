"""Pruebas de fallos, propagación y concurrencia del DAG sgfood_elt."""
import json
import os
import subprocess
import time
import pytest
from conftest import run_docker_compose
from sgfood_ingesta.config import listar_fuentes


def copiar_fixture(proyecto1_dir, fixture_rel_path, dest_container_path):
    """Copia una carpeta de fixtures al contenedor airflow-scheduler y asegura permisos."""
    src = os.path.join(proyecto1_dir, fixture_rel_path)
    run_docker_compose("exec", "-T", "airflow-scheduler", "mkdir", "-p", "/tmp/fixtures", cwd=proyecto1_dir)
    subprocess.run(["docker", "cp", src, f"sgfood_airflow_scheduler:{dest_container_path}"], check=True)
    run_docker_compose("exec", "-T", "--user", "0", "airflow-scheduler", "chown", "-R", "airflow:root", "/tmp/fixtures", cwd=proyecto1_dir)


def disparar_dag(proyecto1_dir, dag_id, conf=None):
    """Dispara un DAG de Airflow y retorna el run_id."""
    args = ["exec", "-T", "airflow-scheduler", "airflow", "dags", "trigger", dag_id]
    if conf:
        args.extend(["--conf", json.dumps(conf)])
    args.extend(["-o", "json"])
    res = run_docker_compose(*args, cwd=proyecto1_dir)
    assert res.returncode == 0, f"Error al disparar DAG {dag_id}: {res.stderr}"
    lineas = [l.strip() for l in res.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
    assert len(lineas) > 0, f"No se encontró JSON en trigger:\n{res.stdout}"
    data = json.loads(lineas[-1])
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("dag_run_id") or data[0].get("run_id")
    elif isinstance(data, dict):
        return data.get("dag_run_id") or data.get("run_id")
    raise ValueError(f"No se pudo extraer run_id de: {res.stdout}")


def esperar_dag_run(proyecto1_dir, dag_id, run_id, timeout=120):
    """Espera que un run de DAG termine con success o failed."""
    start = time.time()
    while time.time() - start < timeout:
        res = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list-runs", dag_id, "-o", "json", cwd=proyecto1_dir)
        if res.returncode == 0:
            lineas = [l.strip() for l in res.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
            if lineas:
                try:
                    runs = json.loads(lineas[-1])
                    for r in runs:
                        curr_id = r.get("dag_run_id") or r.get("run_id")
                        if curr_id == run_id:
                            st = r.get("state")
                            if st in ["success", "failed"]:
                                return st
                except json.JSONDecodeError:
                    pass
        time.sleep(2)
    raise TimeoutError(f"El run {run_id} no terminó en {timeout}s")


def obtener_estados_tareas(proyecto1_dir, dag_id, run_id):
    """Obtiene los estados de cada tarea para un DAG run específico."""
    res = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "tasks", "states-for-dag-run", dag_id, run_id, "-o", "json", cwd=proyecto1_dir)
    lineas = [l.strip() for l in res.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
    assert len(lineas) > 0, f"No se encontró JSON en states-for-dag-run:\n{res.stdout}"
    tis = json.loads(lineas[-1])
    return {ti.get("task_id"): ti.get("state") for ti in tis}


def obtener_filas_raw_totales(proyecto1_dir):
    """Cuenta el total de filas en todas las tablas del schema raw."""
    script = (
        "from sgfood_ingesta.config import listar_fuentes\n"
        "from sgfood_ingesta.conexiones import conectar_dw\n"
        "conn = conectar_dw()\n"
        "total = 0\n"
        "with conn.cursor() as cur:\n"
        "    for f in listar_fuentes():\n"
        "        cur.execute(f'SELECT count(*) FROM raw.{f.tabla_raw}')\n"
        "        total += cur.fetchone()[0]\n"
        "conn.close()\n"
        "print(f'TOTAL_RAW={total}')\n"
    )
    res = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-c", script, cwd=proyecto1_dir)
    assert res.returncode == 0, f"Error al contar raw: {res.stderr}"
    for line in res.stdout.splitlines():
        if "TOTAL_RAW=" in line:
            return int(line.split("=")[1].strip())
    raise ValueError(f"No se encontró TOTAL_RAW en salida: {res.stdout}")


@pytest.mark.integracion
def test_fallo_dbt_modelo_roto(proyecto1_dir):
    """Con dbt_modelo_roto: dbt_run termina en failed; dbt_test y validar_marts quedan sin ejecutar; la ejecución termina en failed; raw conserva 8864 filas."""
    dag_id = "sgfood_elt"
    run_id = None
    try:
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "unpause", "-y", dag_id, cwd=proyecto1_dir)
        copiar_fixture(proyecto1_dir, "tests/dag/fixtures/dbt_modelo_roto", "/tmp/fixtures/dbt_modelo_roto")

        conf = {
            "dbt_project_dir": "/tmp/fixtures/dbt_modelo_roto",
            "dbt_profiles_dir": "/tmp/fixtures/dbt_modelo_roto",
        }
        run_id = disparar_dag(proyecto1_dir, dag_id, conf)
        estado = esperar_dag_run(proyecto1_dir, dag_id, run_id)
        assert estado == "failed", f"La ejecución debió terminar en 'failed', terminó en '{estado}'"

        estados = obtener_estados_tareas(proyecto1_dir, dag_id, run_id)
        assert estados.get("dbt_run") == "failed", f"dbt_run debió ser 'failed', fue '{estados.get('dbt_run')}'"

        # dbt_test y validar_marts no deben haberse ejecutado
        st_dbt_test = estados.get("dbt_test")
        st_val_marts = estados.get("validar_marts")
        assert st_dbt_test in [None, "upstream_failed", "skipped"], f"dbt_test no debió ejecutarse, fue '{st_dbt_test}'"
        assert st_val_marts in [None, "upstream_failed", "skipped"], f"validar_marts no debió ejecutarse, fue '{st_val_marts}'"

        # raw conserva sus 8864 filas
        total_raw = obtener_filas_raw_totales(proyecto1_dir)
        assert total_raw == 8864, f"raw debió conservar 8864 filas, tiene {total_raw}"

    finally:
        run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", "DROP SCHEMA IF EXISTS dag_test CASCADE;", cwd=proyecto1_dir)
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "pause", "-y", dag_id, cwd=proyecto1_dir)


@pytest.mark.integracion
def test_fallo_dbt_prueba_falla(proyecto1_dir):
    """Con dbt_prueba_falla: dbt_run en success, dbt_test en failed, validar_marts sin ejecutar."""
    dag_id = "sgfood_elt"
    run_id = None
    try:
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "unpause", "-y", dag_id, cwd=proyecto1_dir)
        copiar_fixture(proyecto1_dir, "tests/dag/fixtures/dbt_prueba_falla", "/tmp/fixtures/dbt_prueba_falla")

        conf = {
            "dbt_project_dir": "/tmp/fixtures/dbt_prueba_falla",
            "dbt_profiles_dir": "/tmp/fixtures/dbt_prueba_falla",
        }
        run_id = disparar_dag(proyecto1_dir, dag_id, conf)
        estado = esperar_dag_run(proyecto1_dir, dag_id, run_id)
        assert estado == "failed", f"La ejecución debió terminar en 'failed', terminó en '{estado}'"

        estados = obtener_estados_tareas(proyecto1_dir, dag_id, run_id)
        assert estados.get("dbt_run") == "success", f"dbt_run debió ser 'success', fue '{estados.get('dbt_run')}'"
        assert estados.get("dbt_test") == "failed", f"dbt_test debió ser 'failed', fue '{estados.get('dbt_test')}'"

        st_val_marts = estados.get("validar_marts")
        assert st_val_marts in [None, "upstream_failed", "skipped"], f"validar_marts no debió ejecutarse, fue '{st_val_marts}'"

    finally:
        run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", "DROP SCHEMA IF EXISTS dag_test CASCADE;", cwd=proyecto1_dir)
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "pause", "-y", dag_id, cwd=proyecto1_dir)


@pytest.mark.integracion
def test_fallo_validaciones_marts(proyecto1_dir):
    """Con validaciones_falla: validar_marts en failed y su registro nombra el archivo."""
    dag_id = "sgfood_elt"
    run_id = None
    try:
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "unpause", "-y", dag_id, cwd=proyecto1_dir)
        copiar_fixture(proyecto1_dir, "tests/dag/fixtures/dbt_ok", "/tmp/fixtures/dbt_ok")
        copiar_fixture(proyecto1_dir, "tests/dag/fixtures/validaciones_falla", "/tmp/fixtures/validaciones_falla")

        conf = {
            "dbt_project_dir": "/tmp/fixtures/dbt_ok",
            "dbt_profiles_dir": "/tmp/fixtures/dbt_ok",
            "validaciones_dir": "/tmp/fixtures/validaciones_falla",
        }
        run_id = disparar_dag(proyecto1_dir, dag_id, conf)
        estado = esperar_dag_run(proyecto1_dir, dag_id, run_id)
        assert estado == "failed", f"La ejecución debió terminar en 'failed', terminó en '{estado}'"

        estados = obtener_estados_tareas(proyecto1_dir, dag_id, run_id)
        assert estados.get("dbt_run") == "success", f"dbt_run debió ser 'success', fue '{estados.get('dbt_run')}'"
        assert estados.get("dbt_test") == "success", f"dbt_test debió ser 'success', fue '{estados.get('dbt_test')}'"
        assert estados.get("validar_marts") == "failed", f"validar_marts debió ser 'failed', fue '{estados.get('validar_marts')}'"

        # Verificar que el log de validar_marts nombra el archivo que falló
        logs_base = os.path.join(proyecto1_dir, "airflow", "logs", "dag_id=sgfood_elt")
        contenido_log = ""
        log_encontrado = False
        for root, dirs, files in os.walk(logs_base):
            if "task_id=validar_marts" in root:
                for file in files:
                    if file.endswith(".log"):
                        with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as lf:
                            contenido_log += lf.read()
                        log_encontrado = True

        assert log_encontrado, "No se encontró log para validar_marts"
        assert ("01_falla.sql" in contenido_log or "02_falla.sql" in contenido_log), (
            f"El log de validar_marts no nombra el archivo de validación fallido:\n{contenido_log}"
        )

    finally:
        run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", "DROP SCHEMA IF EXISTS dag_test CASCADE;", cwd=proyecto1_dir)
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "pause", "-y", dag_id, cwd=proyecto1_dir)


@pytest.mark.integracion
def test_concurrencia_max_active_runs_una_activa(proyecto1_dir):
    """Con dos ejecuciones disparadas seguidas: la segunda no inicia tareas hasta que la primera termina."""
    dag_id = "sgfood_elt"
    run_id1 = None
    run_id2 = None
    try:
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "unpause", "-y", dag_id, cwd=proyecto1_dir)
        copiar_fixture(proyecto1_dir, "tests/dag/fixtures/dbt_ok", "/tmp/fixtures/dbt_ok")

        conf = {
            "dbt_project_dir": "/tmp/fixtures/dbt_ok",
            "dbt_profiles_dir": "/tmp/fixtures/dbt_ok",
        }
        run_id1 = disparar_dag(proyecto1_dir, dag_id, conf)
        time.sleep(1)
        run_id2 = disparar_dag(proyecto1_dir, dag_id, conf)

        # Inmediatamente tras disparar ambos:
        # mientras run_id1 está corriendo, comprobar que run_id2 está en queued y no tiene tareas corriendo ni exitosas
        res_tis2 = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "tasks", "states-for-dag-run", dag_id, run_id2, "-o", "json", cwd=proyecto1_dir)
        if res_tis2.returncode == 0:
            lineas = [l.strip() for l in res_tis2.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
            if lineas:
                try:
                    tis2 = json.loads(lineas[-1])
                    tareas_iniciadas = [ti for ti in tis2 if ti.get("state") in ["running", "success"]]
                    assert len(tareas_iniciadas) == 0, f"La segunda ejecución no debió iniciar tareas mientras la primera corre: {tareas_iniciadas}"
                except json.JSONDecodeError:
                    pass

        # Esperar que la primera termine
        st1 = esperar_dag_run(proyecto1_dir, dag_id, run_id1)
        assert st1 == "success"

        # Ahora la segunda debe correr y terminar
        st2 = esperar_dag_run(proyecto1_dir, dag_id, run_id2)
        assert st2 == "success"

    finally:
        run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", "DROP SCHEMA IF EXISTS dag_test CASCADE;", cwd=proyecto1_dir)
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "pause", "-y", dag_id, cwd=proyecto1_dir)
