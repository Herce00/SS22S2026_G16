"""R2, R7: ingresos solo de ventas COMPLETADA y validaciones finales que detectan casos invalidos."""
import os
from decimal import Decimal

import pytest

from cierre_utils import escalar, psql

pytestmark = pytest.mark.integracion

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALIDACIONES = os.path.join(RAIZ, "sql", "validaciones")


def _leer(*ruta):
    with open(os.path.join(VALIDACIONES, *ruta), encoding="utf-8") as f:
        return f.read()


def test_ventas_por_sucursal_suma_solo_ventas_completadas():
    filas = psql(_leer("02_ventas_por_sucursal.sql"))
    esperado = Decimal(escalar(
        "SELECT SUM(d.subtotal) FROM oltp_sgfood.venta_detalle d "
        "JOIN oltp_sgfood.venta v USING (id_venta) WHERE v.estado = 'COMPLETADA'", servicio="src"))
    # columnas: sucursal, ventas, unidades, ingresos, ventas_anuladas, ventas_pendientes
    assert len(filas[0]) == 6, f"se esperaban 6 columnas, hay {len(filas[0])}"
    assert sum(Decimal(f[3]) for f in filas) == esperado

    def con_lineas(estado):
        return int(escalar(
            "SELECT COUNT(DISTINCT v.id_venta) FROM oltp_sgfood.venta v "
            f"JOIN oltp_sgfood.venta_detalle d USING (id_venta) WHERE v.estado = '{estado}'",
            servicio="src"))
    assert sum(int(f[4]) for f in filas) == con_lineas("ANULADA")
    assert sum(int(f[5]) for f in filas) == con_lineas("PENDIENTE")


def test_metas_vs_ventas_usa_el_mismo_criterio():
    filas = psql(_leer("03_metas_vs_ventas.sql"))
    # columnas: periodo, sucursal, meta_ventas, ventas_reales, meta_unidades, unidades_reales
    total = sum(Decimal(f[3]) for f in filas)
    base = (
        "SELECT SUM(v.subtotal) FROM marts.fct_ventas_linea v WHERE EXISTS ("
        "SELECT 1 FROM marts.fct_metas_ventas m WHERE m.periodo_key / 100 = v.fecha_key / 100 "
        "AND m.sucursal_key = v.sucursal_key)"
    )
    assert total == Decimal(escalar(base + " AND v.estado = 'COMPLETADA'"))
    assert total != Decimal(escalar(base)), "el total no cambia al filtrar: no se aplico el criterio"


def test_conteos_cubren_las_doce_tablas():
    nombres = {f[0] for f in psql(_leer("01_conteos_marts.sql"))}
    assert len(nombres) == 12


# --- validaciones del DAG contra una copia de marts -------------------------------------------

TABLAS = [
    "dim_categoria", "dim_cliente", "dim_fecha", "dim_marca", "dim_producto", "dim_promocion",
    "dim_sucursal", "fct_devoluciones", "fct_inventario_snapshot", "fct_metas_ventas",
    "fct_precios_proveedor", "fct_ventas_linea",
]

INT_FILE = "01_integridad_referencial_marts.sql"
REG_FILE = "02_reglas_negocio_marts.sql"

# hecho -> (columna clave, expresion de la primera fila)
_PRIMERA = {
    "fct_ventas_linea": ("id_detalle", "marts_cierre.fct_ventas_linea"),
    "fct_inventario_snapshot": ("inventario_snapshot_key", "marts_cierre.fct_inventario_snapshot"),
    "fct_devoluciones": ("devolucion_key", "marts_cierre.fct_devoluciones"),
    "fct_metas_ventas": ("meta_key", "marts_cierre.fct_metas_ventas"),
    "fct_precios_proveedor": ("precio_proveedor_key", "marts_cierre.fct_precios_proveedor"),
}


def _set(hecho, asignacion):
    clave, tabla = _PRIMERA[hecho]
    return f"UPDATE {tabla} SET {asignacion} WHERE {clave} = (SELECT min({clave}) FROM {tabla})"


# (archivo, etiqueta que debe aparecer, modificacion sobre la copia)
CASOS = [
    (INT_FILE, "ventas_fecha", _set("fct_ventas_linea", "fecha_key = 19000101")),
    (INT_FILE, "ventas_cliente", _set("fct_ventas_linea", "cliente_key = 'x'")),
    (INT_FILE, "ventas_sucursal", _set("fct_ventas_linea", "sucursal_key = 'x'")),
    (INT_FILE, "ventas_producto", _set("fct_ventas_linea", "producto_key = 'x'")),
    (INT_FILE, "inventario_fecha", _set("fct_inventario_snapshot", "fecha_key = 19000101")),
    (INT_FILE, "inventario_producto", _set("fct_inventario_snapshot", "producto_key = 'x'")),
    (INT_FILE, "inventario_sucursal", _set("fct_inventario_snapshot", "sucursal_key = 'x'")),
    (INT_FILE, "devoluciones_fecha", _set("fct_devoluciones", "fecha_key = 19000101")),
    (INT_FILE, "devoluciones_producto", _set("fct_devoluciones", "producto_key = 'x'")),
    (INT_FILE, "metas_fecha", _set("fct_metas_ventas", "periodo_key = 19000101")),
    (INT_FILE, "metas_sucursal", _set("fct_metas_ventas", "sucursal_key = 'x'")),
    (INT_FILE, "precios_fecha", _set("fct_precios_proveedor", "fecha_key = 19000101")),
    (INT_FILE, "precios_producto", _set("fct_precios_proveedor", "producto_key = 'x'")),
    (REG_FILE, "ventas_cantidad_no_positiva", _set("fct_ventas_linea", "cantidad = 0")),
    (REG_FILE, "ventas_subtotal_nulo", _set("fct_ventas_linea", "subtotal = NULL")),
    (REG_FILE, "ventas_descuento_fuera_de_rango", _set("fct_ventas_linea", "descuento = 1.5")),
    (REG_FILE, "inventario_stock_nulo", _set("fct_inventario_snapshot", "stock_disponible = NULL")),
    (REG_FILE, "inventario_minimo_mayor_maximo", _set("fct_inventario_snapshot", "stock_minimo = stock_maximo + 1")),
    (REG_FILE, "devolucion_cantidad_no_positiva", _set("fct_devoluciones", "cantidad = 0")),
    (REG_FILE, "metas_valores_nulos", _set("fct_metas_ventas", "meta_ventas = NULL")),
    (REG_FILE, "precios_costo_nulo", _set("fct_precios_proveedor", "costo_proveedor = NULL")),
]


@pytest.fixture(scope="module")
def copia_marts():
    limpiar = "DROP SCHEMA IF EXISTS marts_cierre CASCADE;"
    psql(limpiar)
    psql("CREATE SCHEMA marts_cierre;" + "".join(
        f"CREATE TABLE marts_cierre.{t} AS SELECT * FROM marts.{t};" for t in TABLAS))
    try:
        yield
    finally:
        psql(limpiar)


def _validar(archivo, modificacion=None):
    """Ejecuta la validacion contra marts_cierre dentro de una transaccion que se revierte.

    Devuelve las etiquetas (primera columna) de las filas que la validacion produjo.
    """
    sql = _leer("dag", archivo).replace("marts.", "marts_cierre.").strip().rstrip(";")
    marca = "--FILAS--"
    cuerpo = (
        "BEGIN;" + (f"{modificacion};" if modificacion else "")
        + f"SELECT '{marca}';{sql};ROLLBACK;"
    )
    salida = [fila[0] for fila in psql(cuerpo) if fila]
    return [e for e in salida[salida.index(marca) + 1:] if e != "ROLLBACK"]


@pytest.mark.parametrize("archivo", [INT_FILE, REG_FILE])
def test_validaciones_sin_casos_invalidos_devuelven_cero_filas(copia_marts, archivo):
    assert _validar(archivo) == []


@pytest.mark.parametrize("archivo,etiqueta,modificacion", CASOS, ids=[c[1] for c in CASOS])
def test_cada_validacion_detecta_su_caso_invalido(copia_marts, archivo, etiqueta, modificacion):
    resultado = _validar(archivo, modificacion)
    assert etiqueta in resultado, f"{etiqueta} no detectado; salida: {resultado}"
