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
    "AIRFLOW_JWT_SECRET",
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

def test_no_default_credentials_and_fails_without_admin_password(proyecto1_dir, tmp_path):
    """Verifica que ningún valor del compose contenga contraseña literal o valor por defecto para usuarios/contraseñas, y que sin AIRFLOW_ADMIN_PASSWORD falle nombrándola."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        compose_content = f.read()

    # Verificar que no hayan valores por defecto con ':-' en variables de usuario o contraseña
    for var in ["AIRFLOW_ADMIN_USER", "AIRFLOW_ADMIN_PASSWORD", "DW_PASSWORD", "SRC_PASSWORD", "AIRFLOW_DB_PASSWORD"]:
        assert f"${{{var}:-" not in compose_content, f"{var} tiene valor por defecto con ':-' en docker-compose.yml"

    # Crear un .env temporal con todas las variables requeridas excepto AIRFLOW_ADMIN_PASSWORD
    env_lines = []
    real_env = os.path.join(proyecto1_dir, ".env")
    if os.path.exists(real_env):
        with open(real_env, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    k = line.split("=")[0].strip()
                    if k != "AIRFLOW_ADMIN_PASSWORD":
                        env_lines.append(line)
    temp_env = tmp_path / "test.env"
    temp_env.write_text("".join(env_lines), encoding="utf-8")

    # Ejecutar docker compose --env-file <temp_env> config sin AIRFLOW_ADMIN_PASSWORD
    res = run_docker_compose("--env-file", str(temp_env), "config", cwd=proyecto1_dir)
    assert res.returncode != 0, "docker compose config debió fallar sin AIRFLOW_ADMIN_PASSWORD"
    assert "AIRFLOW_ADMIN_PASSWORD" in (res.stderr + res.stdout), "El error de docker compose config debe nombrar AIRFLOW_ADMIN_PASSWORD"

