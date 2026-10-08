import time
import pytest
from conftest import run_docker_compose

@pytest.mark.lenta
def test_reinicio_limpio(proyecto1_dir):
    """Verifica que down -v y up -d reinicie el entorno a un estado limpio sin datos previos."""
    # 1. Crear tabla temporal en dw
    create_tbl_cmd = "CREATE TABLE raw.tmp_reinicio (id int);"
    res_create = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", create_tbl_cmd, cwd=proyecto1_dir)
    assert res_create.returncode == 0, f"No se pudo crear tabla temporal: {res_create.stderr}"

    # 2. Ejecutar docker compose down -v
    res_down = run_docker_compose("down", "-v", cwd=proyecto1_dir)
    assert res_down.returncode == 0, f"docker compose down -v falló: {res_down.stderr}"

    # 3. Ejecutar docker compose up -d
    res_up = run_docker_compose("up", "-d", cwd=proyecto1_dir)
    assert res_up.returncode == 0, f"docker compose up -d falló: {res_up.stderr}"

    # 4. Esperar a que los servicios se estabilicen (hasta 60 segundos)
    max_wait = 60
    start_time = time.time()
    all_healthy = False

    while time.time() - start_time < max_wait:
        res_ps = run_docker_compose("ps", cwd=proyecto1_dir)
        # Revisar si apiserver, scheduler, dw, src y airflow-db están healthy
        out = res_ps.stdout
        if (
            "sgfood_dw" in out and "(healthy)" in out and
            "sgfood_src" in out and
            "sgfood_airflow_db" in out and
            "sgfood_airflow_scheduler" in out and
            "sgfood_airflow_dag_processor" in out
        ):
            # Verificar si apiserver también está healthy o running
            if "sgfood_airflow_apiserver" in out and "(healthy)" in out:
                all_healthy = True
                break
        time.sleep(5)

    assert all_healthy, f"Los servicios no alcanzaron el estado healthy en {max_wait}s:\n{res_ps.stdout}"

    # 5. Exigir que la tabla temporal ya no exista
    check_tbl_cmd = "SELECT 1 FROM information_schema.tables WHERE table_schema = 'raw' AND table_name = 'tmp_reinicio';"
    res_check = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-t", "-A", "-c", check_tbl_cmd, cwd=proyecto1_dir)
    assert res_check.returncode == 0
    assert res_check.stdout.strip() == "", "La tabla temporal todavía existe tras down -v"

    # 6. Exigir que los tres schemas existan
    check_schemas = "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'staging', 'marts');"
    res_sch = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-t", "-A", "-c", check_schemas, cwd=proyecto1_dir)
    assert res_sch.returncode == 0
    schemas = set(res_sch.stdout.strip().splitlines())
    assert {"raw", "staging", "marts"}.issubset(schemas), f"Schemas faltantes: {schemas}"
