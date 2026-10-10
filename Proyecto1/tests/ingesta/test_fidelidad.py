"""Pruebas de fidelidad y representación de datos entre fuentes y raw (T7)."""
from collections import Counter
import os
import re
import pytest
from conftest import run_docker_compose

from sgfood_ingesta.config import listar_fuentes
from sgfood_ingesta.conexiones import conectar_dw, conectar_src
from sgfood_ingesta.extraccion import extraer_filas_csv


@pytest.fixture(autouse=True)
def configurar_entorno_host(monkeypatch, env_config):
    """Configura las variables de entorno para que el host pueda conectarse a los puertos expuestos."""
    monkeypatch.setenv("DW_HOST", "localhost")
    monkeypatch.setenv("DW_PORT", env_config.get("DW_PORT", "5443"))
    monkeypatch.setenv("DW_DB", env_config.get("DW_DB", "sgfood_dw"))
    monkeypatch.setenv("DW_USER", env_config.get("DW_USER", "dw_user"))
    monkeypatch.setenv("DW_PASSWORD", env_config.get("DW_PASSWORD", ""))

    monkeypatch.setenv("SRC_HOST", "localhost")
    monkeypatch.setenv("SRC_PORT", env_config.get("SRC_PORT", "5444"))
    monkeypatch.setenv("SRC_DB", env_config.get("SRC_DB", "sgfood_src"))
    monkeypatch.setenv("SRC_USER", env_config.get("SRC_USER", "src_user"))
    monkeypatch.setenv("SRC_PASSWORD", env_config.get("SRC_PASSWORD", ""))


@pytest.mark.integracion
def test_fidelidad_fuentes_postgres():
    """Para cada fuente postgres, las filas fuente (::text) y las de raw son iguales con multiplicidad."""
    fuentes_pg = [f for f in listar_fuentes() if f.tipo == "postgres"]

    with conectar_src() as conn_src, conectar_dw() as conn_dw:
        for fuente in fuentes_pg:
            schema, tabla = fuente.origen.split(".", 1)
            cols_src = ", ".join(f'"{c}"::text' for c in fuente.columnas)
            cols_raw = ", ".join(f'"{c}"' for c in fuente.columnas)

            with conn_src.cursor() as cur_src:
                cur_src.execute(f'SELECT {cols_src} FROM "{schema}"."{tabla}";')
                filas_src = [tuple(row) for row in cur_src]

            with conn_dw.cursor() as cur_raw:
                cur_raw.execute(f'SELECT {cols_raw} FROM raw."{fuente.tabla_raw}";')
                filas_raw = [tuple(row) for row in cur_raw]

            assert Counter(filas_src) == Counter(filas_raw), (
                f"Discrepancia en contenido entre {fuente.origen} y raw.{fuente.tabla_raw}"
            )


@pytest.mark.integracion
def test_fidelidad_fuentes_csv(proyecto1_dir):
    """Para cada fuente csv, las filas leídas del archivo y las de raw son iguales con multiplicidad."""
    fuentes_csv = [f for f in listar_fuentes() if f.tipo == "csv"]
    data_dir = os.path.join(proyecto1_dir, "data")

    with conectar_dw() as conn_dw:
        for fuente in fuentes_csv:
            ruta_csv = os.path.join(data_dir, fuente.origen)
            filas_csv = list(extraer_filas_csv(ruta_csv, fuente.columnas))

            cols_raw = ", ".join(f'"{c}"' for c in fuente.columnas)
            with conn_dw.cursor() as cur_raw:
                cur_raw.execute(f'SELECT {cols_raw} FROM raw."{fuente.tabla_raw}";')
                filas_raw = [tuple(row) for row in cur_raw]

            assert Counter(filas_csv) == Counter(filas_raw), (
                f"Discrepancia en contenido entre {fuente.origen} y raw.{fuente.tabla_raw}"
            )


@pytest.mark.integracion
def test_representacion_valores_especificos():
    """Valida representaciones específicas: activo booleano, decimales, fechas y periodos."""
    with conectar_dw() as conn_dw:
        with conn_dw.cursor() as cur:
            # 1. producto.activo solo contiene 'true' o 'false'
            cur.execute("SELECT DISTINCT activo FROM raw.producto;")
            activos = set(row[0] for row in cur)
            assert activos.issubset({"true", "false"}), f"Valores inesperados en producto.activo: {activos}"

            # 2. venta_detalle.descuento cumple siempre formato de cuatro decimales
            cur.execute("SELECT descuento FROM raw.venta_detalle WHERE descuento IS NOT NULL;")
            pattern_cuatro_decimales = re.compile(r"^\d+\.\d{4}$")
            for row in cur:
                assert pattern_cuatro_decimales.match(row[0]), (
                    f"venta_detalle.descuento '{row[0]}' no cumple cuatro decimales"
                )

            # 3. Fechas en formato YYYY-MM-DD
            pattern_fecha = re.compile(r"^\d{4}-\d{2}-\d{2}$")

            cur.execute("SELECT fecha FROM raw.venta WHERE fecha IS NOT NULL;")
            for row in cur:
                assert pattern_fecha.match(row[0]), f"venta.fecha '{row[0]}' no cumple YYYY-MM-DD"

            cur.execute("SELECT fecha_alta FROM raw.cliente WHERE fecha_alta IS NOT NULL;")
            for row in cur:
                assert pattern_fecha.match(row[0]), f"cliente.fecha_alta '{row[0]}' no cumple YYYY-MM-DD"

            cur.execute("SELECT fecha_corte FROM raw.inventario_bodega WHERE fecha_corte IS NOT NULL;")
            for row in cur:
                assert pattern_fecha.match(row[0]), f"inventario_bodega.fecha_corte '{row[0]}' no cumple YYYY-MM-DD"

            # 4. metas_ventas.periodo cumple YYYY-MM
            cur.execute("SELECT periodo FROM raw.metas_ventas WHERE periodo IS NOT NULL;")
            pattern_periodo = re.compile(r"^\d{4}-\d{2}$")
            for row in cur:
                assert pattern_periodo.match(row[0]), f"metas_ventas.periodo '{row[0]}' no cumple YYYY-MM"


@pytest.mark.integracion
def test_conteo_nulos_cliente_coincide():
    """Los nulos de cliente.municipio y cliente.departamento en raw son tantos como en la fuente."""
    with conectar_src() as conn_src, conectar_dw() as conn_dw:
        with conn_src.cursor() as cur_src, conn_dw.cursor() as cur_dw:
            cur_src.execute(
                "SELECT count(*) FILTER (WHERE municipio IS NULL), "
                "       count(*) FILTER (WHERE departamento IS NULL) "
                "FROM oltp_sgfood.cliente;"
            )
            src_nulls_mun, src_nulls_dep = cur_src.fetchone()

            cur_dw.execute(
                "SELECT count(*) FILTER (WHERE municipio IS NULL), "
                "       count(*) FILTER (WHERE departamento IS NULL) "
                "FROM raw.cliente;"
            )
            dw_nulls_mun, dw_nulls_dep = cur_dw.fetchone()

            assert dw_nulls_mun == src_nulls_mun, (
                f"Nulos de municipio en raw ({dw_nulls_mun}) != fuente ({src_nulls_mun})"
            )
            assert dw_nulls_dep == src_nulls_dep, (
                f"Nulos de departamento en raw ({dw_nulls_dep}) != fuente ({src_nulls_dep})"
            )


@pytest.mark.integracion
def test_sin_cadenas_vacias_en_columnas_de_negocio():
    """Ninguna columna de negocio de ninguna tabla en raw contiene una cadena vacía."""
    fuentes = listar_fuentes()
    with conectar_dw() as conn_dw:
        with conn_dw.cursor() as cur:
            for fuente in fuentes:
                for col in fuente.columnas:
                    cur.execute(f"SELECT count(*) FROM raw.\"{fuente.tabla_raw}\" WHERE \"{col}\" = '';")
                    count_vacias = cur.fetchone()[0]
                    assert count_vacias == 0, (
                        f"raw.{fuente.tabla_raw}.{col} contiene {count_vacias} cadenas vacias"
                    )
