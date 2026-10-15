"""R5: claves primarias y foraneas fisicas en marts, que sobreviven a ejecuciones sucesivas."""
import os

import pytest

from cierre_utils import dbt_run_ok, psql, volcado_marts

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REFERENCIA = os.path.join(RAIZ, "sql", "ddl", "referencia", "03_marts_referencia.sql")

TABLAS = [
    "dim_categoria", "dim_cliente", "dim_fecha", "dim_marca", "dim_producto", "dim_promocion",
    "dim_sucursal", "fct_devoluciones", "fct_inventario_snapshot", "fct_metas_ventas",
    "fct_precios_proveedor", "fct_ventas_linea",
]

# (tabla, columna, dimension a la que apunta, columna de la dimension)
FORANEAS = [
    ("fct_ventas_linea", "fecha_key", "dim_fecha", "fecha_key"),
    ("fct_ventas_linea", "cliente_key", "dim_cliente", "cliente_key"),
    ("fct_ventas_linea", "sucursal_key", "dim_sucursal", "sucursal_key"),
    ("fct_ventas_linea", "producto_key", "dim_producto", "producto_key"),
    ("fct_inventario_snapshot", "fecha_key", "dim_fecha", "fecha_key"),
    ("fct_inventario_snapshot", "sucursal_key", "dim_sucursal", "sucursal_key"),
    ("fct_inventario_snapshot", "producto_key", "dim_producto", "producto_key"),
    ("fct_devoluciones", "fecha_key", "dim_fecha", "fecha_key"),
    ("fct_devoluciones", "producto_key", "dim_producto", "producto_key"),
    ("fct_metas_ventas", "periodo_key", "dim_fecha", "fecha_key"),
    ("fct_metas_ventas", "sucursal_key", "dim_sucursal", "sucursal_key"),
    ("fct_precios_proveedor", "fecha_key", "dim_fecha", "fecha_key"),
    ("fct_precios_proveedor", "producto_key", "dim_producto", "producto_key"),
    ("dim_producto", "categoria_key", "dim_categoria", "categoria_key"),
    ("dim_producto", "marca_key", "dim_marca", "marca_key"),
    ("dim_promocion", "fecha_inicio_key", "dim_fecha", "fecha_key"),
    ("dim_promocion", "fecha_fin_key", "dim_fecha", "fecha_key"),
    ("dim_promocion", "categoria_key", "dim_categoria", "categoria_key"),
]


def restricciones():
    """({tabla con PK}, {(tabla, columna, dimension, columna_dimension)}) segun pg_constraint."""
    pks = {f[0] for f in psql(
        "SELECT conrelid::regclass::text FROM pg_constraint c "
        "JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = 'marts' AND c.contype = 'p'"
    )}
    pks = {p.split(".")[-1] for p in pks}
    fks = set()
    for t, col, dim, cdim in psql(
        "SELECT cl.relname, a.attname, rf.relname, af.attname "
        "FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace "
        "JOIN pg_class cl ON cl.oid = c.conrelid JOIN pg_class rf ON rf.oid = c.confrelid "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1] "
        "JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = c.confkey[1] "
        "WHERE n.nspname = 'marts' AND c.contype = 'f'"
    ):
        fks.add((t, col, dim, cdim))
    return pks, fks


@pytest.mark.integracion
@pytest.mark.parametrize("ejecucion", [1, 2])
def test_claves_fisicas_existen_tras_cada_ejecucion(ejecucion):
    dbt_run_ok()
    pks, fks = restricciones()
    assert pks == set(TABLAS), f"tablas sin clave primaria: {set(TABLAS) - pks}"
    assert set(FORANEAS) <= fks, f"claves foraneas faltantes: {sorted(set(FORANEAS) - fks)}"


@pytest.mark.integracion
def test_ddl_de_referencia_coincide_con_la_base():
    assert os.path.exists(REFERENCIA), "falta sql/ddl/referencia/03_marts_referencia.sql"
    with open(REFERENCIA, encoding="utf-8") as f:
        contenido = f.read()
    encabezado = contenido.split("-- ---- fin del encabezado ----\n")
    assert len(encabezado) == 2
    for requisito in ("referencia generada", "pg_dump --schema-only --schema=marts", "dbt crea", "no se ejecuta"):
        assert requisito in encabezado[0]
    assert encabezado[1].strip() + "\n" == volcado_marts(), "el DDL de referencia no coincide con la base: regenerarlo"
    assert contenido.count("CREATE TABLE marts.") == len(TABLAS)
    assert "PRIMARY KEY" in contenido and "FOREIGN KEY" in contenido


def test_ddl_de_referencia_no_esta_en_la_raiz_de_initdb():
    ddl = os.path.join(RAIZ, "sql", "ddl")
    sql_en_raiz = [f for f in os.listdir(ddl) if f.endswith(".sql")]
    assert "03_marts_referencia.sql" not in sql_en_raiz
