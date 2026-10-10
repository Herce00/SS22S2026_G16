import json
import time
import pytest
from conftest import run_docker_compose

@pytest.mark.lenta
def test_reinicio_limpio(proyecto1_dir, env_config):
    """Verifica que down -v y up -d reinicie el entorno a un estado limpio sin datos previos."""
    dw_user = env_config.get("DW_USER", "dw_user")
    dw_db = env_config.get("DW_DB", "sgfood_dw")

    # 1. Crear tabla temporal en dw
    create_tbl_cmd = "CREATE TABLE raw.tmp_reinicio (id int);"
    res_create = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-c", create_tbl_cmd, cwd=proyecto1_dir)
    assert res_create.returncode == 0, f"No se pudo crear tabla temporal: {res_create.stderr}"

    # 2. Ejecutar docker compose down -v
    res_down = run_docker_compose("down", "-v", cwd=proyecto1_dir)
    assert res_down.returncode == 0, f"docker compose down -v falló: {res_down.stderr}"

    # 3. Ejecutar docker compose up -d
    res_up = run_docker_compose("up", "-d", cwd=proyecto1_dir)
    assert res_up.returncode == 0, f"docker compose up -d falló: {res_up.stderr}"

    # 4. Esperar a que CADA servicio de larga duración alcance estado healthy individualmente
    long_running_services = ["dw", "src", "airflow-db", "airflow-apiserver", "airflow-scheduler", "airflow-dag-processor"]
    max_wait = 90
    start_time = time.time()
    all_healthy = False
    service_status = {}

    while time.time() - start_time < max_wait:
        res_ps = run_docker_compose("ps", "--format", "json", cwd=proyecto1_dir)
        if res_ps.returncode == 0:
            service_status = {}
            for line in res_ps.stdout.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    c = json.loads(line)
                    svc = c.get("Service")
                    health = c.get("Health")
                    service_status[svc] = health
                except json.JSONDecodeError:
                    pass
            if all(service_status.get(s) == "healthy" for s in long_running_services):
                all_healthy = True
                break
        time.sleep(5)

    assert all_healthy, f"No todos los servicios alcanzaron 'healthy' en {max_wait}s. Estados observados: {service_status}"

    # 5. Exigir que la tabla temporal ya no exista
    check_tbl_cmd = "SELECT 1 FROM information_schema.tables WHERE table_schema = 'raw' AND table_name = 'tmp_reinicio';"
    res_check = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", check_tbl_cmd, cwd=proyecto1_dir)
    assert res_check.returncode == 0
    assert res_check.stdout.strip() == "", "La tabla temporal todavía existe tras down -v"

    # 6. Exigir que los tres schemas existan
    check_schemas = "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'staging', 'marts');"
    res_sch = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", check_schemas, cwd=proyecto1_dir)
    assert res_sch.returncode == 0
    schemas = set(res_sch.stdout.strip().splitlines())
    assert {"raw", "staging", "marts"}.issubset(schemas), f"Schemas faltantes: {schemas}"

    # 7. Exigir que tras el arranque y dos ciclos del scheduler, sgfood_elt existe, está en pausa y no tiene ejecuciones
    time.sleep(10)
    res_dags = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list", "-o", "json", cwd=proyecto1_dir)
    assert res_dags.returncode == 0
    lineas_dags = [l.strip() for l in res_dags.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
    dags_list = json.loads(lineas_dags[-1]) if lineas_dags else []
    dag_ids = {d.get("dag_id"): d.get("is_paused") for d in dags_list}
    assert "sgfood_elt" in dag_ids, f"DAG sgfood_elt no encontrado tras reinicio: {dag_ids}"
    assert str(dag_ids["sgfood_elt"]).lower() == "true", f"sgfood_elt debe crearse en pausa (is_paused=True), obtenido: {dag_ids['sgfood_elt']}"

    res_runs = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list-runs", "sgfood_elt", "-o", "json", cwd=proyecto1_dir)
    assert res_runs.returncode == 0
    lineas_runs = [l.strip() for l in res_runs.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
    runs_list = json.loads(lineas_runs[-1]) if lineas_runs else []
    assert len(runs_list) == 0, f"sgfood_elt no debe tener ejecuciones tras arranque limpio: {runs_list}"
