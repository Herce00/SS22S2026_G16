import os
import subprocess
import yaml
import pytest
from conftest import run_docker_compose

def test_bases_compose_declarations(proyecto1_dir):
    """Verifica estáticamente la declaración de dw y src en docker-compose.yml."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml no existe"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    assert "dw" in services, "Servicio dw no declarado en docker-compose.yml"
    assert "src" in services, "Servicio src no declarado en docker-compose.yml"

    for s_name in ["dw", "src"]:
        s = services[s_name]
        image = s.get("image", "")
        assert image, f"Servicio {s_name} debe tener una imagen definida"
        assert not image.endswith(":latest") and image != "postgres", f"Servicio {s_name} no debe usar 'latest'"
        assert image == "postgres:16", f"Servicio {s_name} debe usar postgres:16"
        assert "healthcheck" in s, f"Servicio {s_name} debe tener healthcheck"
        assert "volumes" in s, f"Servicio {s_name} debe tener volúmenes definidos"

    # Verificar volúmenes nombrados
    volumes = compose.get("volumes", {})
    assert "dw_data" in volumes, "Volumen nombrado dw_data no definido"
    assert "src_data" in volumes, "Volumen nombrado src_data no definido"

def test_compose_fails_without_dw_password(proyecto1_dir, tmp_path):
    """Verifica que docker compose config falle si falta una variable obligatoria."""
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("DW_DB=sgfood_dw\nDW_USER=dw_user\n", encoding="utf-8")
    res = run_docker_compose("--env-file", str(empty_env), "config", cwd=proyecto1_dir)
    assert res.returncode != 0
    assert "DW_PASSWORD" in (res.stderr + res.stdout)

@pytest.mark.integracion
def test_bases_healthy_and_responsive(proyecto1_dir):
    """Verifica que dw y src estén healthy y respondan SELECT 1."""
    # Verificar salud de dw
    res_dw = run_docker_compose("exec", "-T", "dw", "pg_isready", cwd=proyecto1_dir)
    assert res_dw.returncode == 0, f"dw pg_isready falló: {res_dw.stderr}"

    # Consulta SELECT 1 en dw
    res_sql_dw = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", "SELECT 1;", cwd=proyecto1_dir)
    assert res_sql_dw.returncode == 0 and "1" in res_sql_dw.stdout

    # Verificar salud de src
    res_src = run_docker_compose("exec", "-T", "src", "pg_isready", cwd=proyecto1_dir)
    assert res_src.returncode == 0, f"src pg_isready falló: {res_src.stderr}"

    # Consulta SELECT 1 en src
    res_sql_src = run_docker_compose("exec", "-T", "src", "psql", "-U", "src_user", "-d", "sgfood_src", "-c", "SELECT 1;", cwd=proyecto1_dir)
    assert res_sql_src.returncode == 0 and "1" in res_sql_src.stdout
