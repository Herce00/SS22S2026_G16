"""R1.2, R1.3: el hecho incremental refleja los cambios de la fuente y sigue siendo incremental."""
import os

import pytest

from cierre_utils import (
    TOTAL_RAW_CONTRATO, dbt_run_ok, escalar, psql, raw_intacto, recargar_tabla_raw, total_raw,
)  # noqa: F401

pytestmark = pytest.mark.integracion

RAIZ_DBT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dbt_project")


def test_hecho_sigue_materializado_como_incremental():
    with open(os.path.join(RAIZ_DBT, "models", "marts", "fct_ventas_linea.sql"), encoding="utf-8") as f:
        sql = f.read()
    assert "materialized='incremental'" in sql
    assert "unique_key='id_detalle'" in sql


def test_cambio_de_estado_en_la_fuente_llega_al_hecho(raw_intacto):
    dbt_run_ok(full_refresh=True)
    id_venta = escalar(
        "SELECT min(id_venta) FROM oltp_sgfood.venta WHERE estado = 'PENDIENTE'", servicio="src"
    )
    lineas = escalar(f"SELECT count(*) FROM marts.fct_ventas_linea WHERE id_venta = {id_venta}")
    assert int(lineas) > 0
    assert escalar(f"SELECT count(DISTINCT estado) FROM marts.fct_ventas_linea WHERE id_venta = {id_venta}") == "1"
    assert escalar(f"SELECT max(estado) FROM marts.fct_ventas_linea WHERE id_venta = {id_venta}") == "PENDIENTE"
    try:
        psql(f"UPDATE oltp_sgfood.venta SET estado = 'ANULADA' WHERE id_venta = {id_venta}", servicio="src")
        recargar_tabla_raw("venta")
        dbt_run_ok()
        assert escalar(
            f"SELECT count(*) FROM marts.fct_ventas_linea WHERE id_venta = {id_venta} AND estado = 'ANULADA'"
        ) == lineas
        assert escalar("SELECT count(*) FROM marts.fct_ventas_linea") == "3209"
    finally:
        psql(f"UPDATE oltp_sgfood.venta SET estado = 'PENDIENTE' WHERE id_venta = {id_venta}", servicio="src")
        recargar_tabla_raw("venta")
        dbt_run_ok()
        assert escalar(f"SELECT max(estado) FROM marts.fct_ventas_linea WHERE id_venta = {id_venta}") == "PENDIENTE"
        assert total_raw() == TOTAL_RAW_CONTRATO
