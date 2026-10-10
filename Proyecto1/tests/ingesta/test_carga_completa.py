"""Pruebas de integración para la carga completa y auditoría (T6)."""
import time
import pytest
from conftest import run_docker_compose

from sgfood_ingesta.config import listar_fuentes

EXPECTED_ROW_COUNTS = {
    "sucursal": 6,
    "categoria": 8,
    "marca": 10,
    "producto": 80,
    "cliente": 250,
    "venta": 1200,
    "venta_detalle": 3209,
    "inventario_bodega": 3840,
    "proveedores_precios": 103,
    "devoluciones": 80,
    "metas_ventas": 48,
    "promociones": 30,
}


@pytest.mark.integracion
def test_carga_completa_y_auditoria(proyecto1_dir, env_config):
    """Ejecuta una carga completa y valida conteos, auditoría compartida y aislamiento."""
    dw_user = env_config.get("DW_USER", "dw_user")
    dw_db = env_config.get("DW_DB", "sgfood_dw")
    src_user = env_config.get("SRC_USER", "src_user")
    src_db = env_config.get("SRC_DB", "sgfood_src")

    fuentes = listar_fuentes()
    assert len(fuentes) == 12

    # 1. Ejecutar carga completa sin argumentos
    res = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", cwd=proyecto1_dir)
    assert res.returncode == 0, f"Carga completa falló ({res.returncode}):\n{res.stderr}\n{res.stdout}"

    # 2. Comprobar conteos individuales y total de 8864 filas en raw
    total_filas = 0
    loaded_at_por_tabla = {}

    for f in fuentes:
        tabla = f.tabla_raw
        expected = EXPECTED_ROW_COUNTS[tabla]

        # Conteo de filas
        q_count = f"SELECT count(*) FROM raw.{tabla};"
        res_count = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", q_count, cwd=proyecto1_dir)
        assert res_count.returncode == 0
        cnt = int(res_count.stdout.strip())
        assert cnt == expected, f"raw.{tabla} tiene {cnt} filas, esperadas {expected}"
        total_filas += cnt

        # _source tiene un único valor, igual al origen declarado
        q_source = f"SELECT DISTINCT _source FROM raw.{tabla};"
        res_src = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", q_source, cwd=proyecto1_dir)
        assert res_src.returncode == 0
        sources = res_src.stdout.strip().splitlines()
        assert len(sources) == 1, f"raw.{tabla} tiene múltiples _source: {sources}"
        assert sources[0].strip() == f.origen, f"raw.{tabla} _source='{sources[0]}' != esperado '{f.origen}'"

        # _loaded_at tiene un único valor
        q_loaded = f"SELECT DISTINCT _loaded_at FROM raw.{tabla};"
        res_loaded = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", q_loaded, cwd=proyecto1_dir)
        assert res_loaded.returncode == 0
        loaded_vals = res_loaded.stdout.strip().splitlines()
        assert len(loaded_vals) == 1, f"raw.{tabla} tiene múltiples _loaded_at: {loaded_vals}"
        loaded_at_por_tabla[tabla] = loaded_vals[0].strip()

    assert total_filas == 8864, f"Total de filas en raw es {total_filas}, esperado 8864"

    # 3. Las 12 tablas comparten un único valor de _loaded_at
    todos_loaded_at = set(loaded_at_por_tabla.values())
    assert len(todos_loaded_at) == 1, f"Las 12 tablas tienen distintos _loaded_at: {todos_loaded_at}"
    loaded_at_inicial = list(todos_loaded_at)[0]

    # 4. Cargar solo devoluciones después de una breve pausa
    time.sleep(1)
    res_dev = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--tabla", "devoluciones", cwd=proyecto1_dir)
    assert res_dev.returncode == 0

    # Comprobar que _loaded_at de devoluciones es posterior y las otras 11 tablas no cambiaron
    res_q_dev_loaded = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT DISTINCT _loaded_at FROM raw.devoluciones;", cwd=proyecto1_dir)
    dev_nuevo_loaded = res_q_dev_loaded.stdout.strip()
    assert dev_nuevo_loaded != loaded_at_inicial, "El _loaded_at de devoluciones no cambió tras recarga"

    for f in fuentes:
        if f.tabla_raw == "devoluciones":
            continue
        res_q_other = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", f"SELECT DISTINCT _loaded_at FROM raw.{f.tabla_raw};", cwd=proyecto1_dir)
        assert res_q_other.stdout.strip() == loaded_at_inicial, f"raw.{f.tabla_raw} cambió su _loaded_at inesperadamente"

    # 5. Los conteos de la fuente oltp_sgfood no cambiaron
    for tabla, expected in EXPECTED_ROW_COUNTS.items():
        if tabla in ["inventario_bodega", "proveedores_precios", "devoluciones", "metas_ventas", "promociones"]:
            continue
        res_src_cnt = run_docker_compose("exec", "-T", "src", "psql", "-U", src_user, "-d", src_db, "-t", "-A", "-c", f"SELECT count(*) FROM oltp_sgfood.{tabla};", cwd=proyecto1_dir)
        assert res_src_cnt.returncode == 0
        assert int(res_src_cnt.stdout.strip()) == expected, f"oltp_sgfood.{tabla} fue alterada"

    # 6. staging y marts siguen sin tablas
    q_schemas = "SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('staging', 'marts');"
    res_schemas = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", q_schemas, cwd=proyecto1_dir)
    assert res_schemas.returncode == 0
    assert res_schemas.stdout.strip() == "0", "Los schemas staging o marts tienen tablas creadas inesperadamente"
