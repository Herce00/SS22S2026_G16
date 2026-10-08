import os
import subprocess
import urllib.request
import yaml
import pytest
from conftest import run_docker_compose

def test_airflow_compose_declarations_static(proyecto1_dir):
    """Verifica estáticamente la declaración de los servicios de Airflow en docker-compose.yml."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    assert os.path.exists(compose_path)

    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    required_services = [
        "airflow-db",
        "airflow-init",
        "airflow-apiserver",
        "airflow-scheduler",
        "airflow-dag-processor",
    ]
    for s_name in required_services:
        assert s_name in services, f"Servicio {s_name} no declarado en docker-compose.yml"

    # Verificar que no existen servicios innecesarios
    for forbidden in ["redis", "worker", "flower"]:
        assert forbidden not in services, f"Servicio prohibido {forbidden} encontrado en docker-compose.yml"

    # Verificar variables comunes de Airflow
    for s_name in ["airflow-apiserver", "airflow-scheduler", "airflow-dag-processor"]:
        s = services[s_name]
        env = s.get("environment", {})
        if isinstance(env, list):
            env = dict(item.split("=", 1) for item in env if "=" in item)

        # LocalExecutor
        assert env.get("AIRFLOW__CORE__EXECUTOR") == "LocalExecutor", f"{s_name} debe usar LocalExecutor"
        # load_examples=False
        assert str(env.get("AIRFLOW__CORE__LOAD_EXAMPLES", "")).lower() == "false", f"{s_name} debe tener LOAD_EXAMPLES=False"

        # Dependencias de inicio
        depends_on = s.get("depends_on", {})
        assert "airflow-init" in depends_on, f"{s_name} debe depender de airflow-init"

@pytest.mark.integracion
def test_airflow_services_healthy_and_functional(proyecto1_dir):
    """Verifica la salud de los servicios de Airflow, el endpoint de salud y lista de DAGs."""
    # Verificar que airflow-init terminó con 0
    res_init = run_docker_compose("ps", "-a", "airflow-init", "--format", "{{.Status}}", cwd=proyecto1_dir)
    assert "Exited (0)" in res_init.stdout or "exited with code 0" in res_init.stdout.lower()

    # Verificar salud del endpoint HTTP de Airflow
    env_path = os.path.join(proyecto1_dir, ".env")
    port = "8080"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("AIRFLOW_PORT="):
                    port = line.split("=")[1].strip()

    health_url = f"http://localhost:{port}/api/v2/monitor/health"
    try:
        req = urllib.request.urlopen(health_url, timeout=10)
        assert req.status == 200
    except Exception as e:
        pytest.fail(f"No se pudo consultar {health_url}: {e}")

    # Verificar que la lista de DAGs está vacía (sin ejemplos)
    res_dags = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list", cwd=proyecto1_dir)
    assert res_dags.returncode == 0
    # No deben haber DAGs de ejemplo listados
    assert "example_" not in res_dags.stdout
