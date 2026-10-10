"""Pruebas de tolerancia a fallos, reversión y preservación de datos (T8)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from conftest import run_docker_compose

from sgfood_ingesta.carga import cargar_fuente_en_dw
from sgfood_ingesta.config import Fuente
from sgfood_ingesta.conexiones import conectar_dw
from sgfood_ingesta.errores import ConteoInconsistente


@pytest.fixture(autouse=True)
def configurar_entorno_host(monkeypatch, env_config):
    """Configura las variables de entorno para conexión directa desde el host."""
    monkeypatch.setenv("DW_HOST", "localhost")
    monkeypatch.setenv("DW_PORT", env_config.get("DW_PORT", "5443"))
    monkeypatch.setenv("DW_DB", env_config.get("DW_DB", "sgfood_dw"))
    monkeypatch.setenv("DW_USER", env_config.get("DW_USER", "dw_user"))
    monkeypatch.setenv("DW_PASSWORD", env_config.get("DW_PASSWORD", ""))


@pytest.fixture(scope="module")
def carga_base(proyecto1_dir):
    """Asegura que exista una carga completa antes de las pruebas de fallos."""
    res = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", cwd=proyecto1_dir)
    assert res.returncode == 0, f"Carga base previa falló:\n{res.stderr}"


@pytest.fixture
def fixtures_dir_en_contenedor(proyecto1_dir):
    """Prepara un directorio temporal con copias de los CSV dentro de airflow-scheduler."""
    temp_dir = "/tmp/fixtures_test"
    # Crear directorio y copiar archivos originales de datos
    run_docker_compose("exec", "-T", "airflow-scheduler", "mkdir", "-p", temp_dir, cwd=proyecto1_dir)
    run_docker_compose(
        "exec", "-T", "airflow-scheduler", "bash", "-c",
        f"cp /opt/airflow/data/*.csv {temp_dir}/",
        cwd=proyecto1_dir,
    )
    yield temp_dir
    # Limpieza
    run_docker_compose("exec", "-T", "airflow-scheduler", "rm", "-rf", temp_dir, cwd=proyecto1_dir)


@pytest.mark.integracion
def test_encabezado_incorrecto_preserva_datos(proyecto1_dir, env_config, carga_base, fixtures_dir_en_contenedor):
    """Encabezado incorrecto en promociones.csv: código 1 y conserva 30 filas y _loaded_at."""
    dw_user = env_config.get("DW_USER", "dw_user")
    dw_db = env_config.get("DW_DB", "sgfood_dw")

    # Guardar _loaded_at previo
    res_q_prev = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT DISTINCT _loaded_at FROM raw.promociones;", cwd=proyecto1_dir)
    loaded_at_prev = res_q_prev.stdout.strip()

    # Escribir encabezado malo en la copia temporal
    run_docker_compose(
        "exec", "-T", "airflow-scheduler", "bash", "-c",
        f"echo 'id_incorrecto,nombre_malo' > {fixtures_dir_en_contenedor}/promociones.csv",
        cwd=proyecto1_dir,
    )

    # Ejecutar ingesta apuntando a fixtures temporales
    res = run_docker_compose(
        "exec", "-T", "-e", f"SGFOOD_DATA_DIR={fixtures_dir_en_contenedor}",
        "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--tabla", "promociones",
        cwd=proyecto1_dir,
    )
    assert res.returncode == 1, f"Se esperaba código 1 ante encabezado inválido, obtenido {res.returncode}"

    # Comprobar que conserva filas y _loaded_at
    res_cnt = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT count(*) FROM raw.promociones;", cwd=proyecto1_dir)
    assert res_cnt.stdout.strip() == "30", "Las filas de raw.promociones cambiaron tras fallo"

    res_loaded = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT DISTINCT _loaded_at FROM raw.promociones;", cwd=proyecto1_dir)
    assert res_loaded.stdout.strip() == loaded_at_prev, "El _loaded_at de raw.promociones cambió tras fallo"


@pytest.mark.integracion
def test_fila_con_campo_de_menos_indica_linea_y_preserva_datos(proyecto1_dir, env_config, carga_base, fixtures_dir_en_contenedor):
    """Fila con campo de menos: código 1, mensaje con número de línea y conserva 30 filas."""
    dw_user = env_config.get("DW_USER", "dw_user")
    dw_db = env_config.get("DW_DB", "sgfood_dw")

    # Inyectar una fila truncada en la línea 12 de promociones.csv
    script = (
        f"head -n 11 {fixtures_dir_en_contenedor}/promociones.csv > /tmp/promo_mod.csv && "
        "echo 'PROMO_CORTO' >> /tmp/promo_mod.csv && "
        f"tail -n +12 {fixtures_dir_en_contenedor}/promociones.csv >> /tmp/promo_mod.csv && "
        f"mv /tmp/promo_mod.csv {fixtures_dir_en_contenedor}/promociones.csv"
    )
    run_docker_compose("exec", "-T", "airflow-scheduler", "bash", "-c", script, cwd=proyecto1_dir)

    res = run_docker_compose(
        "exec", "-T", "-e", f"SGFOOD_DATA_DIR={fixtures_dir_en_contenedor}",
        "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--tabla", "promociones",
        cwd=proyecto1_dir,
    )
    salida = res.stderr + res.stdout
    assert res.returncode == 1, f"Se esperaba código 1, obtenido {res.returncode}:\n{salida}"
    assert "12" in salida, f"El mensaje no incluyó el número de línea 12:\n{salida}"

    res_cnt = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT count(*) FROM raw.promociones;", cwd=proyecto1_dir)
    assert res_cnt.stdout.strip() == "30", "Las filas de raw.promociones cambiaron tras fallo"


@pytest.mark.integracion
def test_archivo_csv_inexistente_preserva_filas(proyecto1_dir, env_config, carga_base, fixtures_dir_en_contenedor):
    """Archivo CSV inexistente: código de salida 1 y la tabla conserva sus filas."""
    dw_user = env_config.get("DW_USER", "dw_user")
    dw_db = env_config.get("DW_DB", "sgfood_dw")

    # Eliminar promociones.csv en el directorio temporal
    run_docker_compose("exec", "-T", "airflow-scheduler", "rm", "-f", f"{fixtures_dir_en_contenedor}/promociones.csv", cwd=proyecto1_dir)

    res = run_docker_compose(
        "exec", "-T", "-e", f"SGFOOD_DATA_DIR={fixtures_dir_en_contenedor}",
        "airflow-scheduler", "python", "-m", "sgfood_ingesta", "--tabla", "promociones",
        cwd=proyecto1_dir,
    )
    assert res.returncode == 1, f"Se esperaba código 1, obtenido {res.returncode}"

    res_cnt = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT count(*) FROM raw.promociones;", cwd=proyecto1_dir)
    assert res_cnt.stdout.strip() == "30", "Las filas de raw.promociones cambiaron tras fallo"


@pytest.mark.integracion
def test_carga_completa_con_fallo_confirma_tablas_anteriores(proyecto1_dir, env_config, carga_base, fixtures_dir_en_contenedor):
    """En carga completa con fallo en última tabla, código 1 y tablas previas confirmadas."""
    dw_user = env_config.get("DW_USER", "dw_user")
    dw_db = env_config.get("DW_DB", "sgfood_dw")

    # Guardar _loaded_at de sucursal previo
    res_prev = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT DISTINCT _loaded_at FROM raw.sucursal;", cwd=proyecto1_dir)
    sucursal_prev_ts = res_prev.stdout.strip()

    # Corromper promociones.csv (última tabla)
    run_docker_compose(
        "exec", "-T", "airflow-scheduler", "bash", "-c",
        f"echo 'encabezado,invalido' > {fixtures_dir_en_contenedor}/promociones.csv",
        cwd=proyecto1_dir,
    )

    res = run_docker_compose(
        "exec", "-T", "-e", f"SGFOOD_DATA_DIR={fixtures_dir_en_contenedor}",
        "airflow-scheduler", "python", "-m", "sgfood_ingesta",
        cwd=proyecto1_dir,
    )
    assert res.returncode == 1, f"Se esperaba código 1, obtenido {res.returncode}"

    # Sucursal (primera tabla) debió haberse cargado y confirmado con un timestamp nuevo
    res_new = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT DISTINCT _loaded_at FROM raw.sucursal;", cwd=proyecto1_dir)
    sucursal_new_ts = res_new.stdout.strip()
    assert sucursal_new_ts != sucursal_prev_ts, "La tabla sucursal debió quedar confirmada con nuevo timestamp"

    # Y promociones mantuvo sus 30 filas intactas
    res_cnt = run_docker_compose("exec", "-T", "dw", "psql", "-U", dw_user, "-d", dw_db, "-t", "-A", "-c", "SELECT count(*) FROM raw.promociones;", cwd=proyecto1_dir)
    assert res_cnt.stdout.strip() == "30"


def test_conteo_inconsistente_lanza_excepcion_y_revierte_transaccion():
    """Conteo inconsistente lanza ConteoInconsistente y revierte la transacción en el DW."""
    # Creamos una tabla temporal en el DW con datos iniciales
    with conectar_dw() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS raw._test_inconsistencia (id text, _loaded_at timestamptz, _source text);")
            cur.execute("TRUNCATE TABLE raw._test_inconsistencia;")
            cur.execute("INSERT INTO raw._test_inconsistencia (id, _loaded_at, _source) VALUES ('fila_original', now(), 'test');")
        conn.commit()

    fuente_test = Fuente(
        tabla_raw="_test_inconsistencia",
        tipo="csv",
        origen="test_fake.csv",
        columnas=("id",),
    )

    # Simulamos que el generador entrega 5 filas pero el count posterior devuelve un valor distinto
    with patch("sgfood_ingesta.carga.extraer_filas_csv") as mock_csv:
        mock_csv.return_value = [("f1",), ("f2",), ("f3",)]

        # Parcheamos cur.fetchone para devolver count=2 en lugar de 3
        with patch("psycopg.Cursor.fetchone", return_value=[2]):
            with pytest.raises(ConteoInconsistente) as exc_info:
                cargar_fuente_en_dw(fuente_test, datetime.now(timezone.utc))

            assert "Discrepancia en tabla '_test_inconsistencia'" in str(exc_info.value)

    # Verificar que tras el error y rollback, la fila original sigue intacta
    with conectar_dw() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM raw._test_inconsistencia;")
            filas_restantes = cur.fetchall()
            assert filas_restantes == [("fila_original",)], (
                f"La transacción no se revirtió: encontradas {filas_restantes}"
            )
            # Limpiar tabla de prueba
            cur.execute("DROP TABLE IF EXISTS raw._test_inconsistencia;")
        conn.commit()
