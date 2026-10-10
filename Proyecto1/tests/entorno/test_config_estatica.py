import os
import subprocess
import yaml
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

def test_no_image_uses_latest_tag(proyecto1_dir):
    """Verifica que ninguna imagen en el compose use la etiqueta 'latest', incluida airflow-db."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    images_checked = []
    if "x-airflow-common" in compose and "image" in compose["x-airflow-common"]:
        images_checked.append(compose["x-airflow-common"]["image"])

    services = compose.get("services", {})
    for svc_name, svc_conf in services.items():
        if "image" in svc_conf:
            images_checked.append(svc_conf["image"])

    assert len(images_checked) > 0, "No se encontraron imágenes declaradas en el compose"
    for img in images_checked:
        assert ":latest" not in img, f"La imagen {img} usa la etiqueta 'latest'"
        assert ":" in img, f"La imagen {img} debe especificar una versión fija y no omitir etiqueta"

def test_dw_and_src_distinct_host_ports(proyecto1_dir, env_config):
    """Verifica que dw y src publiquen puertos del host distintos."""
    dw_port = env_config.get("DW_PORT")
    src_port = env_config.get("SRC_PORT")
    assert dw_port is not None and src_port is not None, "DW_PORT y SRC_PORT deben estar configurados"
    assert dw_port != src_port, f"DW_PORT ({dw_port}) y SRC_PORT ({src_port}) no deben coincidir"

    res = run_docker_compose("config", "--format", "json", cwd=proyecto1_dir)
    assert res.returncode == 0
    import json
    config_data = json.loads(res.stdout)

    services = config_data.get("services", {})
    dw_ports = services.get("dw", {}).get("ports", [])
    src_ports = services.get("src", {}).get("ports", [])

    dw_published = [p.get("published") for p in dw_ports if isinstance(p, dict) and "published" in p]
    src_published = [p.get("published") for p in src_ports if isinstance(p, dict) and "published" in p]
    if dw_published and src_published:
        assert set(dw_published).isdisjoint(set(src_published)), f"Puertos publicados en host colisionan: {dw_published} vs {src_published}"

def test_airflow_services_depend_on_airflow_init(proyecto1_dir):
    """Verifica que los servicios de Airflow dependan de airflow-init con la condición service_completed_successfully."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    airflow_services = ["airflow-apiserver", "airflow-scheduler", "airflow-dag-processor"]

    for svc in airflow_services:
        assert svc in services, f"Servicio {svc} no encontrado en docker-compose.yml"
        deps = services[svc].get("depends_on", {})
        assert "airflow-init" in deps, f"{svc} no depende de airflow-init"
        init_dep = deps["airflow-init"]
        condition = init_dep.get("condition") if isinstance(init_dep, dict) else None
        assert condition == "service_completed_successfully", f"{svc} debe depender de airflow-init con condición 'service_completed_successfully', pero tiene '{condition}'"

def test_pytest_ini_excludes_lenta_by_default(proyecto1_dir):
    """Verifica que pytest.ini exista y configure 'addopts = -m \"not lenta\"' para proteger contra ejecuciones destructivas por defecto."""
    pytest_ini_path = os.path.join(proyecto1_dir, "pytest.ini")
    assert os.path.exists(pytest_ini_path), "pytest.ini no existe en Proyecto1"
    with open(pytest_ini_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert 'addopts = -m "not lenta"' in content, "pytest.ini debe excluir pruebas lentas por defecto con addopts = -m \"not lenta\""


def test_compose_monta_sql_en_airflow_ro(proyecto1_dir):
    """Verifica que el compose monte ./sql en /opt/airflow/sql como solo lectura en los servicios de Airflow."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    common_volumes = compose.get("x-airflow-common", {}).get("volumes", [])
    sql_mounted_ro = any(
        (v == "./sql:/opt/airflow/sql:ro" or
         (isinstance(v, dict) and v.get("target") == "/opt/airflow/sql" and v.get("read_only") is True))
        for v in common_volumes
    )
    assert sql_mounted_ro, "x-airflow-common debe montar ./sql en /opt/airflow/sql como solo lectura (:ro)"


