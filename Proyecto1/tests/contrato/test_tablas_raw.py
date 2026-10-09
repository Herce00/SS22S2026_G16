import os
import pytest
import yaml
from conftest import run_docker_compose


@pytest.fixture(scope="module")
def fuentes_data(proyecto1_dir):
    config_path = os.path.join(proyecto1_dir, "python", "config", "fuentes.yml")
    assert os.path.isfile(config_path), f"fuentes.yml no existe en {config_path}"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.mark.integracion
def test_raw_tables_exist_and_match_fuentes(proyecto1_dir, env_config, fuentes_data):
    """Verifica que el schema raw contenga exactamente las tablas declaradas en fuentes.yml."""
    expected_tables = set(f.get("tabla_raw") for f in fuentes_data.get("fuentes", []))
    assert len(expected_tables) == 12, "fuentes.yml debe declarar 12 tablas"

    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")

    query = (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'raw' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name;"
    )
    res = run_docker_compose("exec", "-T", "dw", "psql", "-U", user, "-d", db, "-t", "-A", "-c", query, cwd=proyecto1_dir)
    assert res.returncode == 0, f"Error consultando tablas en raw: {res.stderr}"

    actual_tables = set(t for t in res.stdout.strip().splitlines() if t)
    assert actual_tables == expected_tables, (
        f"Tablas en schema raw no coinciden.\nEsperadas: {expected_tables}\nEncontradas: {actual_tables}"
    )


@pytest.mark.integracion
def test_raw_columns_types_and_order(proyecto1_dir, env_config, fuentes_data):
    """Verifica que las columnas de cada tabla en raw coincidan en nombre, orden y tipo con el contrato."""
    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")

    for f in fuentes_data.get("fuentes", []):
        tabla = f.get("tabla_raw")
        expected_business_cols = f.get("columnas", [])

        query = (
            f"SELECT column_name, data_type, is_nullable "
            f"FROM information_schema.columns "
            f"WHERE table_schema = 'raw' AND table_name = '{tabla}' "
            f"ORDER BY ordinal_position;"
        )
        res = run_docker_compose("exec", "-T", "dw", "psql", "-U", user, "-d", db, "-t", "-A", "-F", "|", "-c", query, cwd=proyecto1_dir)
        assert res.returncode == 0, f"Error consultando columnas de raw.{tabla}: {res.stderr}"

        lines = [line.strip().split("|") for line in res.stdout.strip().splitlines() if line.strip()]
        assert len(lines) == len(expected_business_cols) + 2, (
            f"raw.{tabla} tiene {len(lines)} columnas, esperadas {len(expected_business_cols) + 2}"
        )

        # Validar columnas de negocio
        for i, expected_name in enumerate(expected_business_cols):
            col_name, data_type, is_nullable = lines[i]
            assert col_name == expected_name, (
                f"raw.{tabla}: columna #{i} esperaba '{expected_name}', encontrada '{col_name}'"
            )
            assert data_type == "text", (
                f"raw.{tabla}.{col_name}: tipo esperado 'text', encontrado '{data_type}'"
            )

        # Validar columnas de auditoria
        loaded_at_name, loaded_at_type, loaded_at_null = lines[-2]
        assert loaded_at_name == "_loaded_at"
        assert loaded_at_type == "timestamp with time zone"
        assert loaded_at_null == "NO"

        source_name, source_type, source_null = lines[-1]
        assert source_name == "_source"
        assert source_type == "text"
        assert source_null == "NO"


@pytest.mark.integracion
def test_raw_tables_have_no_constraints(proyecto1_dir, env_config, fuentes_data):
    """Verifica que ninguna tabla de raw tenga claves primarias, foraneas, UNIQUE ni restricciones CHECK de negocio."""
    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")

    query = (
        "SELECT tc.table_name, tc.constraint_name, tc.constraint_type, COALESCE(cc.check_clause, '') "
        "FROM information_schema.table_constraints tc "
        "LEFT JOIN information_schema.check_constraints cc ON tc.constraint_name = cc.constraint_name "
        "WHERE tc.table_schema = 'raw' "
        "  AND ("
        "    tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE') "
        "    OR (tc.constraint_type = 'CHECK' AND cc.check_clause NOT IN ('_loaded_at IS NOT NULL', '_source IS NOT NULL'))"
        "  );"
    )
    res = run_docker_compose("exec", "-T", "dw", "psql", "-U", user, "-d", db, "-t", "-A", "-F", "|", "-c", query, cwd=proyecto1_dir)
    assert res.returncode == 0, f"Error consultando restricciones de raw: {res.stderr}"

    constraints = [line for line in res.stdout.strip().splitlines() if line]
    assert len(constraints) == 0, f"raw contiene restricciones de negocio no permitidas: {constraints}"


@pytest.mark.integracion
def test_raw_ddl_idempotent(proyecto1_dir, env_config):
    """Verifica que 02_raw_tables.sql pueda ejecutarse nuevamente con ON_ERROR_STOP=1 sin error."""
    user = env_config.get("DW_USER", "dw_user")
    db = env_config.get("DW_DB", "sgfood_dw")

    res = run_docker_compose(
        "exec", "-T", "dw", "psql", "-U", user, "-d", db,
        "-v", "ON_ERROR_STOP=1", "-f", "/docker-entrypoint-initdb.d/02_raw_tables.sql",
        cwd=proyecto1_dir
    )
    assert res.returncode == 0, f"Reejecucion de 02_raw_tables.sql fallo: {res.stderr}"
