"""Pruebas de idempotencia de la ingesta (T8)."""
from collections import Counter
import pytest
from conftest import run_docker_compose

from sgfood_ingesta.config import listar_fuentes
from sgfood_ingesta.conexiones import conectar_dw


@pytest.fixture(autouse=True)
def configurar_entorno_host(monkeypatch, env_config):
    """Configura las variables de entorno para conexión directa desde el host."""
    monkeypatch.setenv("DW_HOST", "localhost")
    monkeypatch.setenv("DW_PORT", env_config.get("DW_PORT", "5443"))
    monkeypatch.setenv("DW_DB", env_config.get("DW_DB", "sgfood_dw"))
    monkeypatch.setenv("DW_USER", env_config.get("DW_USER", "dw_user"))
    monkeypatch.setenv("DW_PASSWORD", env_config.get("DW_PASSWORD", ""))


@pytest.mark.integracion
def test_idempotencia_dos_cargas_completas(proyecto1_dir):
    """Dos cargas completas consecutivas dejan exactamente los mismos conteos y contenidos."""
    fuentes = listar_fuentes()

    # 1. Primera carga completa
    res1 = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", cwd=proyecto1_dir)
    assert res1.returncode == 0, f"Primera carga falló:\n{res1.stderr}"

    contenido_primera_carga = {}
    conteos_primera_carga = {}

    with conectar_dw() as conn:
        with conn.cursor() as cur:
            for f in fuentes:
                cols = ", ".join(f'"{c}"' for c in f.columnas)
                cur.execute(f'SELECT {cols} FROM raw."{f.tabla_raw}";')
                filas = [tuple(row) for row in cur]
                conteos_primera_carga[f.tabla_raw] = len(filas)
                contenido_primera_carga[f.tabla_raw] = Counter(filas)

    # 2. Segunda carga completa
    res2 = run_docker_compose("exec", "-T", "airflow-scheduler", "python", "-m", "sgfood_ingesta", cwd=proyecto1_dir)
    assert res2.returncode == 0, f"Segunda carga falló:\n{res2.stderr}"

    with conectar_dw() as conn:
        with conn.cursor() as cur:
            for f in fuentes:
                cols = ", ".join(f'"{c}"' for c in f.columnas)
                cur.execute(f'SELECT {cols} FROM raw."{f.tabla_raw}";')
                filas = [tuple(row) for row in cur]

                assert len(filas) == conteos_primera_carga[f.tabla_raw], (
                    f"Conteo de raw.{f.tabla_raw} cambió en segunda carga: "
                    f"{len(filas)} != {conteos_primera_carga[f.tabla_raw]}"
                )
                assert Counter(filas) == contenido_primera_carga[f.tabla_raw], (
                    f"Contenido de raw.{f.tabla_raw} difiere entre cargas"
                )
