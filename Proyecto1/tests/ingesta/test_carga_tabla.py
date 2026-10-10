"""Pruebas de carga de una sola tabla e invocación por CLI (T5)."""
import os
import pytest
import yaml
from conftest import run_docker_compose

from sgfood_ingesta.config import listar_fuentes


def test_compose_defines_pythonpath(proyecto1_dir):
    """Verifica estáticamente que los servicios de Airflow definan PYTHONPATH=/opt/airflow/python."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    # Puede estar en x-airflow-common o en los servicios individuales
    common_env = compose.get("x-airflow-common", {}).get("environment", {})
    pythonpath = common_env.get("PYTHONPATH")

    if not pythonpath:
        # Verificar en cada servicio de airflow
        for svc_name in ["airflow-apiserver", "airflow-scheduler", "airflow-dag-processor"]:
            svc_env = compose.get("services", {}).get(svc_name, {}).get("environment", {})
            assert svc_env.get("PYTHONPATH") == "/opt/airflow/python", (
                f"El servicio {svc_name} debe definir PYTHONPATH: /opt/airflow/python"
            )
    else:
        assert pythonpath == "/opt/airflow/python", (
            f"x-airflow-common define PYTHONPATH '{pythonpath}', esperado '/opt/airflow/python'"
        )


def test_src_healthcheck_checks_venta_detalle(proyecto1_dir):
    """Verifica que el healthcheck de src compruebe que oltp_sgfood.venta_detalle tiene filas."""
    compose_path = os.path.join(proyecto1_dir, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    src_health = compose.get("services", {}).get("src", {}).get("healthcheck", {})
    test_cmd = src_health.get("test", [])
    test_str = " ".join(test_cmd) if isinstance(test_cmd, list) else str(test_cmd)

    assert "venta_detalle" in test_str, (
        f"El healthcheck de src debe comprobar oltp_sgfood.venta_detalle, encontrado: {test_str}"
    )
    # Una consulta que devuelve cero filas tambien termina con exito: el resultado debe evaluarse.
    assert "grep -q" in test_str, (
        f"El healthcheck de src debe fallar si la tabla esta vacia, encontrado: {test_str}"
    )
    # Durante los scripts de inicializacion PostgreSQL solo atiende por socket local;
    # consultar por TCP garantiza que la inicializacion ya termino.
    assert "-h 127.0.0.1" in test_str, (
        f"El healthcheck de src debe conectarse por TCP, encontrado: {test_str}"
    )


@pytest.mark.integracion
def test_listar_fuentes_cli(proyecto1_dir):
    """--listar muestra las 12 fuentes configuradas y termina con código 0."""
    res = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--listar", cwd=proyecto1_dir)
    assert res.returncode == 0, f"CLI --listar falló con {res.returncode}:\n{res.stderr}\n{res.stdout}"

    fuentes = listar_fuentes()
    for f in fuentes:
        assert f.tabla_raw in res.stdout, f"Tabla {f.tabla_raw} no aparece en salida de --listar"


@pytest.mark.integracion
def test_tabla_inexistente_retorna_codigo_2(proyecto1_dir):
    """--tabla con tabla desconocida termina con código 2 y lista las tablas válidas."""
    res = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--tabla", "tabla_inexistente", cwd=proyecto1_dir)
    assert res.returncode == 2, f"Esperaba código 2, obtenido {res.returncode}:\n{res.stderr}\n{res.stdout}"

    salida_total = res.stderr + res.stdout
    fuentes = listar_fuentes()
    # Verifica que liste las tablas válidas disponibles
    for f in fuentes:
        assert f.tabla_raw in salida_total, f"Tabla válida {f.tabla_raw} no fue listada en mensaje de error"


@pytest.mark.integracion
def test_carga_tabla_individual_y_no_afecta_otras(proyecto1_dir, env_config):
    """Carga devoluciones y sucursal de forma individual y comprueba conteos y aislamiento."""
    dw_user = env_config.get("DW_USER", "dw_user")
    dw_db = env_config.get("DW_DB", "sgfood_dw")
    dw_pass = env_config.get("DW_PASSWORD", "")

    # 1. Cargar devoluciones (fuente CSV, 80 filas)
    res_dev = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--tabla", "devoluciones", cwd=proyecto1_dir)
    salida_dev = res_dev.stdout + res_dev.stderr
    assert res_dev.returncode == 0, f"Error cargando devoluciones: {salida_dev}"

    # Salida registra origen, destino, filas leídas, filas cargadas, duración
    assert "devoluciones" in salida_dev
    assert "80" in salida_dev
    if dw_pass:
        assert dw_pass not in salida_dev, "La contraseña del DW apareció en los registros de salida"

    # Verificar filas en raw.devoluciones
    q_count_dev = "SELECT count(*) FROM raw.devoluciones;"
    res_q_dev = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", q_count_dev, cwd=proyecto1_dir)
    assert res_q_dev.returncode == 0
    assert res_q_dev.stdout.strip() == "80", f"raw.devoluciones tiene {res_q_dev.stdout.strip()} filas, esperadas 80"

    # 2. Cargar sucursal (fuente Postgres, 6 filas)
    res_suc = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--tabla", "sucursal", cwd=proyecto1_dir)
    salida_suc = res_suc.stdout + res_suc.stderr
    assert res_suc.returncode == 0, f"Error cargando sucursal: {salida_suc}"

    assert "sucursal" in salida_suc
    assert "6" in salida_suc
    if dw_pass:
        assert dw_pass not in salida_suc, "La contraseña del DW apareció en los registros de salida"

    # Verificar filas en raw.sucursal
    q_count_suc = "SELECT count(*) FROM raw.sucursal;"
    res_q_suc = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", q_count_suc, cwd=proyecto1_dir)
    assert res_q_suc.returncode == 0
    assert res_q_suc.stdout.strip() == "6", f"raw.sucursal tiene {res_q_suc.stdout.strip()} filas, esperadas 6"

    # 3. Comprobar que raw.devoluciones sigue teniendo exactamente 80 filas
    res_q_dev2 = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", q_count_dev, cwd=proyecto1_dir)
    assert res_q_dev2.returncode == 0
    assert res_q_dev2.stdout.strip() == "80", "Cargar sucursal alteró las filas de raw.devoluciones"
