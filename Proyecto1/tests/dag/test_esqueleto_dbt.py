"""Pruebas del esqueleto del proyecto dbt."""
import os
import re
import pytest
import yaml
from conftest import run_docker_compose
from sgfood_ingesta.config import listar_fuentes


def test_archivos_esqueleto_dbt_existen(proyecto1_dir):
    """Verifica que existan todos los archivos del esqueleto dbt."""
    dbt_dir = os.path.join(proyecto1_dir, "dbt_project")
    archivos_esperados = [
        os.path.join(dbt_dir, "dbt_project.yml"),
        os.path.join(dbt_dir, "profiles.yml"),
        os.path.join(dbt_dir, "README.md"),
        os.path.join(dbt_dir, "macros", "generate_schema_name.sql"),
        os.path.join(dbt_dir, "models", "staging", "_fuentes.yml"),
        os.path.join(dbt_dir, "models", "staging", "_staging.yml"),
    ]
    for ruta in archivos_esperados:
        assert os.path.exists(ruta), f"Archivo requerido no existe: {ruta}"


def test_profiles_yml_sin_credenciales_literales(proyecto1_dir):
    """profiles.yml no contiene contraseñas, hosts ni usuarios literales: todo sale de env_var."""
    profiles_path = os.path.join(proyecto1_dir, "dbt_project", "profiles.yml")
    assert os.path.exists(profiles_path), f"profiles.yml no existe en {profiles_path}"
    with open(profiles_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Comprobar que usa env_var para las variables de entorno requeridas
    for var in ["DW_HOST", "DW_PORT", "DW_USER", "DW_PASSWORD", "DW_DB"]:
        patron = rf"env_var\(['\"]{var}['\"]\)"
        assert re.search(patron, contenido), f"profiles.yml no usa env_var para {var}"

    # Comprobar que no hay contraseñas literales sospechosas
    for literal in ["password:", "host:", "user:", "dbname:"]:
        for line in contenido.splitlines():
            line_str = line.strip()
            if line_str.startswith(literal) and "env_var" not in line_str:
                pytest.fail(f"Línea con posible valor literal en profiles.yml: {line_str}")


def test_fuentes_dbt_coinciden_con_fuentes_yml(proyecto1_dir):
    """Toda tabla de raw declarada como fuente en el proyecto dbt existe en fuentes.yml."""
    fuentes_config = {f.tabla_raw for f in listar_fuentes()}
    fuentes_dbt_path = os.path.join(proyecto1_dir, "dbt_project", "models", "staging", "_fuentes.yml")
    assert os.path.exists(fuentes_dbt_path), f"_fuentes.yml no existe en {fuentes_dbt_path}"

    with open(fuentes_dbt_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tablas_declaradas = set()
    for source in data.get("sources", []):
        assert source.get("schema") == "{{ var('schema_raw', 'raw') }}", (
            f"El schema de la fuente debe ser raw (parametrizable con schema_raw): {source.get('schema')}"
        )
        for tbl in source.get("tables", []):
            tablas_declaradas.add(tbl.get("name"))

    assert len(tablas_declaradas) > 0, "No se encontraron tablas declaradas en _fuentes.yml"
    for tbl in tablas_declaradas:
        assert tbl in fuentes_config, f"Tabla '{tbl}' en _fuentes.yml no existe en fuentes.yml de ingesta"


def test_dbt_project_yml_valido(proyecto1_dir):
    """dbt_project.yml declara el proyecto, el perfil y las rutas que el DAG espera."""
    ruta = os.path.join(proyecto1_dir, "dbt_project", "dbt_project.yml")
    with open(ruta, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg.get("name") == "sgfood"
    assert cfg.get("profile") == "sgfood"
    assert cfg.get("model-paths") == ["models"]
    assert cfg.get("macro-paths") == ["macros"]


def test_macro_schema_define_generate_schema_name(proyecto1_dir):
    """El macro de schema evita prefijos como staging_staging."""
    ruta = os.path.join(proyecto1_dir, "dbt_project", "macros", "generate_schema_name.sql")
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    assert "macro generate_schema_name" in contenido
    assert "custom_schema_name" in contenido


def test_fuentes_dbt_declaran_las_tablas_de_raw(proyecto1_dir):
    """_fuentes.yml declara las 12 tablas de raw de fuentes.yml, ni mas ni menos."""
    esperadas = {f.tabla_raw for f in listar_fuentes()}
    assert len(esperadas) == 12
    ruta = os.path.join(proyecto1_dir, "dbt_project", "models", "staging", "_fuentes.yml")
    with open(ruta, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    declaradas = {t["name"] for s in data["sources"] for t in s["tables"]}
    assert declaradas == esperadas


@pytest.mark.integracion
def test_integracion_dbt_project_ejecucion(proyecto1_dir):
    """Con raw cargado, dentro de airflow-scheduler: dbt debug, dbt run y dbt test terminan con 0;

    staging.stg_oltp__sucursal existe con 6 filas y clave entera; no hay schemas duplicados.
    """
    dbt_bin = "/opt/dbt-venv/bin/dbt"
    project_dir = "/opt/airflow/dbt_project"
    profiles_dir = "/opt/airflow/dbt_project"

    # 1. dbt debug
    res_debug = run_docker_compose("exec", "-T", "airflow-scheduler", dbt_bin, "debug", "--project-dir", project_dir, "--profiles-dir", profiles_dir, cwd=proyecto1_dir)
    assert res_debug.returncode == 0, f"dbt debug falló:\n{res_debug.stdout}\n{res_debug.stderr}"

    # 2. dbt run
    res_run = run_docker_compose("exec", "-T", "airflow-scheduler", dbt_bin, "run", "--project-dir", project_dir, "--profiles-dir", profiles_dir, cwd=proyecto1_dir)
    assert res_run.returncode == 0, f"dbt run falló:\n{res_run.stdout}\n{res_run.stderr}"

    # 3. dbt test
    res_test = run_docker_compose("exec", "-T", "airflow-scheduler", dbt_bin, "test", "--project-dir", project_dir, "--profiles-dir", profiles_dir, cwd=proyecto1_dir)
    assert res_test.returncode == 0, f"dbt test falló:\n{res_test.stdout}\n{res_test.stderr}"

    # 4. Verificar modelo en staging con 6 filas y columna entera
    script_check = (
        "import psycopg\n"
        "from sgfood_ingesta.conexiones import conectar_dw\n"
        "conn = conectar_dw()\n"
        "with conn.cursor() as cur:\n"
        "    cur.execute('SELECT count(*) FROM staging.stg_oltp__sucursal')\n"
        "    cnt = cur.fetchone()[0]\n"
        "    cur.execute(\"SELECT data_type FROM information_schema.columns WHERE table_schema='staging' AND table_name='stg_oltp__sucursal' AND column_name='id_sucursal'\")\n"
        "    dtype = cur.fetchone()[0]\n"
        "    cur.execute(\"SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE '%staging%staging%' OR schema_name LIKE '%marts%marts%'\")\n"
        "    dups = cur.fetchall()\n"
        "conn.close()\n"
        "print(f'CNT={cnt} DTYPE={dtype} DUPS={len(dups)}')\n"
    )
    res_chk = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-c", script_check, cwd=proyecto1_dir)
    assert res_chk.returncode == 0, f"Error al verificar modelo en DW:\n{res_chk.stdout}\n{res_chk.stderr}"
    assert "CNT=6" in res_chk.stdout, f"Se esperaban 6 filas en staging.stg_oltp__sucursal:\n{res_chk.stdout}"
    assert "DTYPE=integer" in res_chk.stdout, f"id_sucursal debe ser integer:\n{res_chk.stdout}"
    assert "DUPS=0" in res_chk.stdout, f"No deben existir schemas duplicados:\n{res_chk.stdout}"


@pytest.mark.integracion
def test_independencia_rol_b_modelo_nuevo(proyecto1_dir):
    """Verifica que Rol B puede agregar un modelo sin cambiar airflow/, python/ ni sql/."""
    dag_id = "sgfood_elt"
    nuevo_modelo_path = os.path.join(proyecto1_dir, "dbt_project", "models", "staging", "stg_oltp__test_independencia.sql")
    run_id = None

    try:
        # 1. Crear modelo nuevo
        with open(nuevo_modelo_path, "w", encoding="utf-8") as f:
            f.write("SELECT 1::int as id_test\n")

        # 2. Despausar y disparar con parámetros predeterminados (sin --conf)
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "unpause", "-y", dag_id, cwd=proyecto1_dir)
        res_trig = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "trigger", dag_id, "-o", "json", cwd=proyecto1_dir)
        import json, time
        lineas_trig = [l.strip() for l in res_trig.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
        trig_data = json.loads(lineas_trig[-1])
        run_id = trig_data[0].get("dag_run_id") or trig_data[0].get("run_id") if isinstance(trig_data, list) else trig_data.get("dag_run_id") or trig_data.get("run_id")

        # 3. Esperar finalización
        estado_final = None
        start = time.time()
        while time.time() - start < 120:
            res_runs = run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "list-runs", dag_id, "-o", "json", cwd=proyecto1_dir)
            if res_runs.returncode == 0:
                lineas = [l.strip() for l in res_runs.stdout.splitlines() if (l.strip().startswith("[") and l.strip().endswith("]")) or (l.strip().startswith("{") and l.strip().endswith("}"))]
                if lineas:
                    runs = json.loads(lineas[-1])
                    for r in runs:
                        curr_id = r.get("dag_run_id") or r.get("run_id")
                        if curr_id == run_id and r.get("state") in ["success", "failed"]:
                            estado_final = r.get("state")
                            break
                    if estado_final:
                        break
            time.sleep(2)

        assert estado_final == "success", f"La ejecución debió terminar en 'success', fue '{estado_final}'"

        # 4. Exigir que el modelo exista en el DW
        res_dw = run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-tAc", "SELECT count(*) FROM staging.stg_oltp__test_independencia;", cwd=proyecto1_dir)
        assert res_dw.returncode == 0, f"Error al consultar nuevo modelo en DW: {res_dw.stderr}"
        assert res_dw.stdout.strip() == "1", f"El nuevo modelo debe tener 1 fila, obtenido: {res_dw.stdout}"

        # 5. Exigir que git status no muestre cambios en airflow/, python/ ni sql/
        import subprocess
        res_git = subprocess.run(["git", "status", "--porcelain", "airflow", "python", "sql"], cwd=proyecto1_dir, capture_output=True, text=True)
        assert res_git.stdout.strip() == "", f"Rutas de Rol A no debieron modificarse: {res_git.stdout}"

    finally:
        if os.path.exists(nuevo_modelo_path):
            os.remove(nuevo_modelo_path)
        run_docker_compose("exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c", "DROP VIEW IF EXISTS staging.stg_oltp__test_independencia CASCADE;", cwd=proyecto1_dir)
        run_docker_compose("exec", "-T", "airflow-scheduler", "airflow", "dags", "pause", "-y", dag_id, cwd=proyecto1_dir)

