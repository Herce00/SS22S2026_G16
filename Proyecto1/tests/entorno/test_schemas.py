import pytest
from conftest import run_docker_compose

@pytest.mark.integracion
def test_schemas_exist_in_dw(proyecto1_dir, env_config):
    """Verifica que raw, staging y marts existan en dw."""
    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")
    query = "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'staging', 'marts');"
    res = run_docker_compose("exec", "-T", "dw", "psql", "-U", user, "-d", db, "-t", "-A", "-c", query, cwd=proyecto1_dir)
    assert res.returncode == 0
    schemas = set(res.stdout.strip().splitlines())
    assert {"raw", "staging", "marts"}.issubset(schemas), f"Faltan schemas en dw: {schemas}"

@pytest.mark.integracion
def test_schemas_have_no_tables(proyecto1_dir, env_config):
    """Verifica que staging y marts no contengan tablas inicialmente."""
    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema IN ('staging', 'marts');"
    res = run_docker_compose("exec", "-T", "dw", "psql", "-U", user, "-d", db, "-t", "-A", "-c", query, cwd=proyecto1_dir)
    assert res.returncode == 0
    tables = [t for t in res.stdout.strip().splitlines() if t]
    assert len(tables) == 0, f"Los schemas no deben contener tablas inicialmente: {tables}"

@pytest.mark.integracion
def test_user_can_create_tables_in_schemas(proyecto1_dir, env_config):
    """Verifica permisos del usuario DW en raw, staging y marts."""
    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")
    for s in ["raw", "staging", "marts"]:
        cmd = f"CREATE TABLE {s}._test_tbl (id int); DROP TABLE {s}._test_tbl;"
        res = run_docker_compose("exec", "-T", "dw", "psql", "-U", user, "-d", db, "-c", cmd, cwd=proyecto1_dir)
        assert res.returncode == 0, f"{user} no tiene permisos en {s}: {res.stderr}"

@pytest.mark.integracion
def test_ddl_script_is_idempotent(proyecto1_dir, env_config):
    """Verifica que el script DDL pueda ejecutarse más de una vez sin error con ON_ERROR_STOP=1."""
    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")
    res = run_docker_compose(
        "exec", "-T", "dw", "psql", "-U", user, "-d", db,
        "-v", "ON_ERROR_STOP=1", "-f", "/docker-entrypoint-initdb.d/01_schemas.sql",
        cwd=proyecto1_dir
    )
    assert res.returncode == 0, f"Reejecución de 01_schemas.sql falló: {res.stderr}"
