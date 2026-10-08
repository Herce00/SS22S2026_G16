import pytest
from conftest import run_docker_compose

@pytest.mark.integracion
def test_schemas_exist_in_dw(proyecto1_dir):
    """Verifica que raw, staging y marts existan en dw."""
    query = "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'staging', 'marts');"
    res = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-t", "-A", "-c", query, cwd=proyecto1_dir)
    assert res.returncode == 0
    schemas = set(res.stdout.strip().splitlines())
    assert {"raw", "staging", "marts"}.issubset(schemas), f"Faltan schemas en dw: {schemas}"

@pytest.mark.integracion
def test_schemas_have_no_tables(proyecto1_dir):
    """Verifica que ningún schema contenga tablas."""
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema IN ('raw', 'staging', 'marts');"
    res = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-t", "-A", "-c", query, cwd=proyecto1_dir)
    assert res.returncode == 0
    tables = [t for t in res.stdout.strip().splitlines() if t]
    assert len(tables) == 0, f"Los schemas no deben contener tablas inicialmente: {tables}"

@pytest.mark.integracion
def test_user_can_create_tables_in_schemas(proyecto1_dir):
    """Verifica permisos del usuario dw_user en raw, staging y marts."""
    for s in ["raw", "staging", "marts"]:
        cmd = f"CREATE TABLE {s}._test_tbl (id int); DROP TABLE {s}._test_tbl;"
        res = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", cmd, cwd=proyecto1_dir)
        assert res.returncode == 0, f"dw_user no tiene permisos en {s}: {res.stderr}"

@pytest.mark.integracion
def test_ddl_script_is_idempotent(proyecto1_dir):
    """Verifica que el script DDL pueda ejecutarse más de una vez sin error."""
    res = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-f", "/docker-entrypoint-initdb.d/01_schemas.sql", cwd=proyecto1_dir)
    assert res.returncode == 0, f"Reejecución de 01_schemas.sql falló: {res.stderr}"
