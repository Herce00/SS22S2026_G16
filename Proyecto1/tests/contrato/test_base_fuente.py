import os
import pytest
import yaml
from conftest import run_docker_compose

EXPECTED_ROW_COUNTS = {
    "sucursal": 6,
    "categoria": 8,
    "marca": 10,
    "producto": 80,
    "cliente": 250,
    "venta": 1200,
    "venta_detalle": 3209,
}


def test_src_compose_mount(proyecto1_dir):
    """Verifica estaticamente que el servicio src monte sgfood_oltp.sql en /docker-entrypoint-initdb.d/ como :ro."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    assert os.path.isfile(compose_path), "docker-compose.yml no existe"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    src_service = compose.get("services", {}).get("src", {})
    volumes = src_service.get("volumes", [])

    found_mount = False
    for v in volumes:
        if isinstance(v, str):
            parts = v.split(":")
            if len(parts) >= 2:
                host_path, container_path = parts[0], parts[1]
                mode = parts[2] if len(parts) > 2 else ""
                if "sgfood_oltp.sql" in host_path and container_path.startswith("/docker-entrypoint-initdb.d/"):
                    assert mode == "ro", f"El montaje de sgfood_oltp.sql debe ser :ro, encontrado: '{mode}'"
                    found_mount = True
                    break

    assert found_mount, (
        "El servicio src no monta './data/sgfood_oltp.sql' en '/docker-entrypoint-initdb.d/' como :ro"
    )


@pytest.mark.integracion
def test_oltp_schema_and_tables(proyecto1_dir, env_config):
    """Verifica que en src exista el schema oltp_sgfood con exactamente 7 tablas."""
    user = env_config.get("SRC_USER", "src_user")
    db = env_config.get("SRC_DB", "sgfood_src")

    query = (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'oltp_sgfood' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name;"
    )
    res = run_docker_compose("exec", "-T", "src", "psql", "-U", user, "-d", db, "-t", "-A", "-c", query, cwd=proyecto1_dir)
    assert res.returncode == 0, f"Error consultando tablas en src: {res.stderr}"

    actual_tables = set(t for t in res.stdout.strip().splitlines() if t)
    expected_tables = set(EXPECTED_ROW_COUNTS.keys())

    assert actual_tables == expected_tables, (
        f"Tablas en oltp_sgfood no coinciden.\nEsperadas: {expected_tables}\nEncontradas: {actual_tables}"
    )


@pytest.mark.integracion
def test_oltp_table_row_counts(proyecto1_dir, env_config):
    """Verifica que cada tabla de oltp_sgfood tenga la cantidad esperada de filas."""
    user = env_config.get("SRC_USER", "src_user")
    db = env_config.get("SRC_DB", "sgfood_src")

    for table, expected_count in EXPECTED_ROW_COUNTS.items():
        query = f"SELECT count(*) FROM oltp_sgfood.{table};"
        res = run_docker_compose("exec", "-T", "src", "psql", "-U", user, "-d", db, "-t", "-A", "-c", query, cwd=proyecto1_dir)
        assert res.returncode == 0, f"Error consultando conteo en src para {table}: {res.stderr}"

        count_str = res.stdout.strip()
        assert count_str.isdigit(), f"Resultado de conteo no valido para {table}: '{count_str}'"
        assert int(count_str) == expected_count, (
            f"Conteo incorrecto para oltp_sgfood.{table}. Esperado: {expected_count}, Obtenido: {count_str}"
        )


@pytest.mark.integracion
def test_oltp_columns_match_fuentes_config(proyecto1_dir, env_config):
    """Verifica que las columnas de cada tabla en src coincidan en nombre y orden con fuentes.yml."""
    config_path = os.path.join(proyecto1_dir, "python", "config", "fuentes.yml")
    with open(config_path, "r", encoding="utf-8") as f:
        fuentes_data = yaml.safe_load(f)

    postgres_fuentes = [f for f in fuentes_data.get("fuentes", []) if f.get("tipo") == "postgres"]
    assert len(postgres_fuentes) == 7, "Se esperaban 7 fuentes postgres en fuentes.yml"

    user = env_config.get("SRC_USER", "src_user")
    db = env_config.get("SRC_DB", "sgfood_src")

    for f in postgres_fuentes:
        tabla = f.get("tabla_raw")
        expected_cols = f.get("columnas", [])

        query = (
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_schema = 'oltp_sgfood' AND table_name = '{tabla}' "
            f"ORDER BY ordinal_position;"
        )
        res = run_docker_compose("exec", "-T", "src", "psql", "-U", user, "-d", db, "-t", "-A", "-c", query, cwd=proyecto1_dir)
        assert res.returncode == 0, f"Error consultando columnas en src para {tabla}: {res.stderr}"

        actual_cols = [c for c in res.stdout.strip().splitlines() if c]
        assert actual_cols == expected_cols, (
            f"Columnas para oltp_sgfood.{tabla} no coinciden.\n"
            f"fuentes.yml: {expected_cols}\n"
            f"Base fuente: {actual_cols}"
        )
