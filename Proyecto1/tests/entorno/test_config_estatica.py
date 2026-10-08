import os
import subprocess
from conftest import run_docker_compose

EXPECTED_ENV_VARS = [
    "DW_DB",
    "DW_USER",
    "DW_PASSWORD",
    "DW_PORT",
    "SRC_DB",
    "SRC_USER",
    "SRC_PASSWORD",
    "SRC_PORT",
    "AIRFLOW_DB_USER",
    "AIRFLOW_DB_PASSWORD",
    "AIRFLOW_ADMIN_USER",
    "AIRFLOW_ADMIN_PASSWORD",
    "AIRFLOW_PORT",
    "AIRFLOW_UID",
]

def test_docker_compose_config(proyecto1_dir):
    """Verifica que 'docker compose config' se ejecute con éxito."""
    res = run_docker_compose("config", cwd=proyecto1_dir)
    assert res.returncode == 0, f"docker compose config falló con retorno {res.returncode}:\n{res.stderr}"

def test_env_example_contains_all_variables(proyecto1_dir):
    """Verifica que .env.example exista y contenga todas las variables requeridas por design.md."""
    env_example_path = os.path.join(proyecto1_dir, ".env.example")
    assert os.path.exists(env_example_path), ".env.example no existe en Proyecto1"
    
    with open(env_example_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    found_vars = set()
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            var_name = line.split("=")[0].strip()
            found_vars.add(var_name)
            
    missing_vars = [var for var in EXPECTED_ENV_VARS if var not in found_vars]
    assert not missing_vars, f"Faltan variables en .env.example: {missing_vars}"

def test_gitignore_exclusions(proyecto1_dir):
    """Verifica que .gitignore o git excluya .env, logs/, target/ y dbt_packages/."""
    # Verificar que .env esté ignorado por git
    env_path = os.path.join(proyecto1_dir, ".env")
    res = subprocess.run(["git", "check-ignore", ".env"], cwd=proyecto1_dir, capture_output=True, text=True)
    assert res.returncode == 0, ".env debe estar ignorado por git"

    # Verificar que los directorios generados estén en las reglas de gitignore
    gitignore_path = os.path.join(proyecto1_dir, ".gitignore")
    assert os.path.exists(gitignore_path), ".gitignore no existe en Proyecto1"
    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()

    for pattern in [".env", "logs/", "target/", "dbt_packages/"]:
        assert pattern in content, f"Patrón {pattern} no encontrado en Proyecto1/.gitignore"

