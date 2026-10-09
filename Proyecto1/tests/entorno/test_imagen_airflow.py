import os
import subprocess
import pytest

def test_dockerfile_and_requirements_static(proyecto1_dir):
    """Verifica estáticamente el Dockerfile y los archivos de requisitos."""
    dockerfile_path = os.path.join(proyecto1_dir, "airflow", "Dockerfile")
    assert os.path.exists(dockerfile_path), "airflow/Dockerfile no existe"

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        df_content = f.read()

    assert "FROM apache/airflow:3.3.2-python3.12" in df_content, "Dockerfile debe basarse en apache/airflow:3.3.2-python3.12"
    assert ":latest" not in df_content, "Dockerfile no debe usar la etiqueta latest"

    # requirements.txt
    req_path = os.path.join(proyecto1_dir, "airflow", "requirements.txt")
    assert os.path.exists(req_path), "airflow/requirements.txt no existe"
    with open(req_path, "r", encoding="utf-8") as f:
        req_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for line in req_lines:
        assert "==" in line, f"Dependencia sin versión exacta (==): {line}"
        pkg_name = line.split("==")[0].strip().lower()
        assert pkg_name != "apache-airflow", "requirements.txt no debe incluir el paquete apache-airflow"
        assert not pkg_name.startswith("dbt"), "requirements.txt no debe incluir dbt"

    # requirements-dbt.txt
    dbt_req_path = os.path.join(proyecto1_dir, "airflow", "requirements-dbt.txt")
    assert os.path.exists(dbt_req_path), "airflow/requirements-dbt.txt no existe"
    with open(dbt_req_path, "r", encoding="utf-8") as f:
        dbt_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    assert "dbt-core==1.12.5" in dbt_lines, "requirements-dbt.txt debe contener dbt-core==1.12.5"
    assert "dbt-postgres==1.11.0" in dbt_lines, "requirements-dbt.txt debe contener dbt-postgres==1.11.0"

@pytest.mark.integracion
def test_airflow_dbt_image_integration(proyecto1_dir):
    """Verifica dentro de la imagen construida las versiones de Airflow y dbt."""
    # Ejecutar airflow version
    res_af = subprocess.run(
        ["docker", "run", "--rm", "sgfood-airflow:3.3.2", "airflow", "version"],
        capture_output=True, text=True
    )
    assert res_af.returncode == 0
    assert "3.3.2" in res_af.stdout

    # Ejecutar which dbt
    res_which = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "which", "sgfood-airflow:3.3.2", "dbt"],
        capture_output=True, text=True
    )
    assert res_which.returncode == 0
    assert "/opt/dbt-venv/bin/dbt" in res_which.stdout

    # Ejecutar dbt --version
    res_dbt = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "dbt", "sgfood-airflow:3.3.2", "--version"],
        capture_output=True, text=True
    )
    assert res_dbt.returncode == 0
    out = res_dbt.stdout
    assert "1.12.5" in out, f"dbt Core 1.12.5 no encontrado en:\n{out}"
    assert "1.11.0" in out, f"dbt-postgres 1.11.0 no encontrado en:\n{out}"
