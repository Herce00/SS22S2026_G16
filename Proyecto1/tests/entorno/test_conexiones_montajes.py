import pytest
from conftest import run_docker_compose

@pytest.mark.integracion
def test_conexiones_airflow(proyecto1_dir):
    """Verifica variables de entorno de conexión y conexiones registradas en Airflow."""
    # Verificar variables de entorno dentro de airflow-scheduler
    cmd_env = ["exec", "-T", "airflow-scheduler", "bash", "-c", "env"]
    res_env = run_docker_compose(*cmd_env, cwd=proyecto1_dir)
    assert res_env.returncode == 0
    env_out = res_env.stdout

    for var in [
        "DW_HOST", "DW_PORT", "DW_DB", "DW_USER", "DW_PASSWORD",
        "SRC_HOST", "SRC_PORT", "SRC_DB", "SRC_USER", "SRC_PASSWORD",
        "AIRFLOW_CONN_SGFOOD_DW", "AIRFLOW_CONN_SGFOOD_SRC",
        "DBT_PROJECT_DIR", "DBT_PROFILES_DIR",
    ]:
        assert f"{var}=" in env_out, f"Variable {var} no presente en airflow-scheduler"

    # Verificar que SELECT 1 responde contra dw y src usando las variables desde el contenedor
    cmd_test_dw = [
        "exec", "-T", "airflow-scheduler", "python", "-c",
        "import os, psycopg; conn = psycopg.connect(host=os.environ['DW_HOST'], port=os.environ['DW_PORT'], dbname=os.environ['DW_DB'], user=os.environ['DW_USER'], password=os.environ['DW_PASSWORD']); cur = conn.cursor(); cur.execute('SELECT 1;'); assert cur.fetchone()[0] == 1"
    ]
    res_dw = run_docker_compose(*cmd_test_dw, cwd=proyecto1_dir)
    assert res_dw.returncode == 0, f"Conexión a DW desde Airflow falló: {res_dw.stderr}"

    cmd_test_src = [
        "exec", "-T", "airflow-scheduler", "python", "-c",
        "import os, psycopg; conn = psycopg.connect(host=os.environ['SRC_HOST'], port=os.environ['SRC_PORT'], dbname=os.environ['SRC_DB'], user=os.environ['SRC_USER'], password=os.environ['SRC_PASSWORD']); cur = conn.cursor(); cur.execute('SELECT 1;'); assert cur.fetchone()[0] == 1"
    ]
    res_src = run_docker_compose(*cmd_test_src, cwd=proyecto1_dir)
    assert res_src.returncode == 0, f"Conexión a SRC desde Airflow falló: {res_src.stderr}"

    # Verificar conexiones registradas en Airflow CLI y su conn_type postgres
    res_conn_dw = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "connections", "get", "sgfood_dw", cwd=proyecto1_dir)
    assert res_conn_dw.returncode == 0, f"Conexión sgfood_dw no encontrada: {res_conn_dw.stderr}"
    assert "postgres " in res_conn_dw.stdout or "| postgres " in res_conn_dw.stdout or "conn_type: postgres" in res_conn_dw.stdout

    res_conn_src = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "connections", "get", "sgfood_src", cwd=proyecto1_dir)
    assert res_conn_src.returncode == 0, f"Conexión sgfood_src no encontrada: {res_conn_src.stderr}"
    assert "postgres " in res_conn_src.stdout or "| postgres " in res_conn_src.stdout or "conn_type: postgres" in res_conn_src.stdout

    # Verificar que PostgresHook construido desde cada conn_id tiene conn_type postgres y ejecuta SELECT 1
    cmd_hook_dw = [
        "exec", "-T", "airflow-scheduler", "python", "-c",
        "from airflow.providers.postgres.hooks.postgres import PostgresHook; "
        "hook = PostgresHook(postgres_conn_id='sgfood_dw'); "
        "conn_meta = hook.get_connection('sgfood_dw'); "
        "assert conn_meta.conn_type == 'postgres', f'conn_type esperado postgres pero fue {conn_meta.conn_type}'; "
        "records = hook.get_records('SELECT 1;'); "
        "assert records[0][0] == 1"
    ]
    res_hook_dw = run_docker_compose(*cmd_hook_dw, cwd=proyecto1_dir)
    assert res_hook_dw.returncode == 0, f"PostgresHook sgfood_dw falló: {res_hook_dw.stderr} {res_hook_dw.stdout}"

    cmd_hook_src = [
        "exec", "-T", "airflow-scheduler", "python", "-c",
        "from airflow.providers.postgres.hooks.postgres import PostgresHook; "
        "hook = PostgresHook(postgres_conn_id='sgfood_src'); "
        "conn_meta = hook.get_connection('sgfood_src'); "
        "assert conn_meta.conn_type == 'postgres', f'conn_type esperado postgres pero fue {conn_meta.conn_type}'; "
        "records = hook.get_records('SELECT 1;'); "
        "assert records[0][0] == 1"
    ]
    res_hook_src = run_docker_compose(*cmd_hook_src, cwd=proyecto1_dir)
    assert res_hook_src.returncode == 0, f"PostgresHook sgfood_src falló: {res_hook_src.stderr} {res_hook_src.stdout}"

@pytest.mark.integracion
def test_montajes_airflow(proyecto1_dir):
    """Verifica la existencia de los directorios montados dentro del contenedor."""
    dirs_to_check = [
        "/opt/airflow/dags",
        "/opt/airflow/python",
        "/opt/airflow/dbt_project",
        "/opt/airflow/data",
    ]
    cmd = f"test -d {' && test -d '.join(dirs_to_check)}"
    res = run_docker_compose("exec", "-T", "airflow-scheduler", "bash", "-c", cmd, cwd=proyecto1_dir)
    assert res.returncode == 0, f"Uno o más directorios montados no existen en el contenedor: {dirs_to_check}"
