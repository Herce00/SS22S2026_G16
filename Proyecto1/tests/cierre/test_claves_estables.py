"""R1.1, R1.4: las claves sustitutas derivan de la clave natural y no cambian entre ejecuciones."""
import pytest

from cierre_utils import (
    TOTAL_RAW_CONTRATO, dbt_run_ok, escalar, psql, raw_intacto, recargar_tabla_raw, total_raw,
)  # noqa: F401

pytestmark = pytest.mark.integracion

DIMENSIONES = {
    "dim_cliente": ("id_cliente", "cliente_key"),
    "dim_producto": ("id_producto", "producto_key"),
    "dim_sucursal": ("id_sucursal", "sucursal_key"),
    "dim_categoria": ("id_categoria", "categoria_key"),
    "dim_marca": ("id_marca", "marca_key"),
    "dim_promocion": ("id_promocion", "promocion_key"),
}


def claves_de_dimensiones():
    return {
        dim: dict(psql(f"SELECT {nat}, {key} FROM marts.{dim}"))
        for dim, (nat, key) in DIMENSIONES.items()
    }


def cliente_de_cada_linea():
    """id_detalle -> id_cliente natural, resuelto a traves de la clave sustituta del hecho."""
    return dict(psql(
        "SELECT f.id_detalle, c.id_cliente FROM marts.fct_ventas_linea f "
        "JOIN marts.dim_cliente c ON c.cliente_key = f.cliente_key"
    ))


def test_dos_ejecuciones_dejan_las_mismas_claves(raw_intacto):
    dbt_run_ok(full_refresh=True)
    antes, filas_antes = claves_de_dimensiones(), cliente_de_cada_linea()
    dbt_run_ok()
    assert claves_de_dimensiones() == antes
    assert cliente_de_cada_linea() == filas_antes
    assert len(filas_antes) == 3209


def test_entidad_nueva_no_reasigna_claves(raw_intacto):
    dbt_run_ok(full_refresh=True)
    antes, lineas_antes = claves_de_dimensiones(), cliente_de_cada_linea()
    assert len(antes["dim_cliente"]) == 250
    assert len(lineas_antes) == 3209
    try:
        psql(
            "INSERT INTO oltp_sgfood.cliente (id_cliente, nit, nombre, tipo_cliente, fecha_alta) "
            "VALUES (0, 'CIERRE-0', 'Cliente de prueba cierre', 'Minorista', DATE '2026-01-01')",
            servicio="src",
        )
        recargar_tabla_raw("cliente")
        dbt_run_ok()
        despues = claves_de_dimensiones()
        assert len(despues["dim_cliente"]) == 251
        existentes = {k: v for k, v in despues["dim_cliente"].items() if k != "0"}
        assert existentes == antes["dim_cliente"], "las claves de los 250 clientes existentes cambiaron"
        assert cliente_de_cada_linea() == lineas_antes, "alguna linea apunta ahora a otro cliente"
    finally:
        psql("DELETE FROM oltp_sgfood.cliente WHERE id_cliente = 0", servicio="src")
        recargar_tabla_raw("cliente")
        dbt_run_ok()
        assert escalar("SELECT count(*) FROM raw.cliente") == "250"
        assert total_raw() == TOTAL_RAW_CONTRATO
