"""R4: cobertura de pruebas dbt (estatica sobre los YAML) y reporte de lineas huerfanas (integracion)."""
import os
import re

import pytest
import yaml

from cierre_utils import copia_raw, dbt, escalar, psql, raw_intacto, resumen  # noqa: F401

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELOS = os.path.join(RAIZ, "dbt_project", "models")


def _columnas(ruta_yml):
    """{modelo: {columna: [pruebas]}} donde cada prueba es (nombre, argumentos)."""
    with open(os.path.join(MODELOS, ruta_yml), encoding="utf-8") as f:
        data = yaml.safe_load(f)
    salida = {}
    for modelo in data["models"]:
        columnas = {}
        for col in modelo.get("columns", []):
            pruebas = []
            for p in col.get("tests", []) + col.get("data_tests", []):
                if isinstance(p, str):
                    pruebas.append((p, {}))
                else:
                    (nombre, args), = p.items()
                    args = args or {}
                    pruebas.append((nombre, args.get("arguments", args)))
            columnas[col["name"]] = pruebas
        salida[modelo["name"]] = columnas
    return salida


MARTS = _columnas("marts/_marts.yml")
STAGING = _columnas("staging/_staging.yml")

CLAVES_SUSTITUTAS = {
    "dim_fecha": "fecha_key", "dim_sucursal": "sucursal_key", "dim_cliente": "cliente_key",
    "dim_categoria": "categoria_key", "dim_marca": "marca_key", "dim_producto": "producto_key",
    "dim_promocion": "promocion_key", "fct_ventas_linea": "venta_linea_key",
    "fct_inventario_snapshot": "inventario_snapshot_key", "fct_devoluciones": "devolucion_key",
    "fct_metas_ventas": "meta_key", "fct_precios_proveedor": "precio_proveedor_key",
}

# (modelo, columna) -> dimension a la que apunta (toda clave foranea de los hechos y de dim_promocion)
FORANEAS = {
    ("fct_ventas_linea", "fecha_key"): "dim_fecha",
    ("fct_ventas_linea", "cliente_key"): "dim_cliente",
    ("fct_ventas_linea", "sucursal_key"): "dim_sucursal",
    ("fct_ventas_linea", "producto_key"): "dim_producto",
    ("fct_inventario_snapshot", "fecha_key"): "dim_fecha",
    ("fct_inventario_snapshot", "sucursal_key"): "dim_sucursal",
    ("fct_inventario_snapshot", "producto_key"): "dim_producto",
    ("fct_devoluciones", "fecha_key"): "dim_fecha",
    ("fct_devoluciones", "producto_key"): "dim_producto",
    ("fct_metas_ventas", "periodo_key"): "dim_fecha",
    ("fct_metas_ventas", "sucursal_key"): "dim_sucursal",
    ("fct_precios_proveedor", "fecha_key"): "dim_fecha",
    ("fct_precios_proveedor", "producto_key"): "dim_producto",
    ("dim_promocion", "fecha_inicio_key"): "dim_fecha",
    ("dim_promocion", "fecha_fin_key"): "dim_fecha",
    ("dim_promocion", "categoria_key"): "dim_categoria",
}

# Valores reales consultados en raw (T1)
CATEGORICAS = {
    ("fct_ventas_linea", "canal"): {"Mayorista", "Televenta", "Tienda", "Web"},
    ("fct_ventas_linea", "metodo_pago"): {"Crédito", "Efectivo", "Tarjeta", "Transferencia"},
    ("fct_ventas_linea", "estado"): {"ANULADA", "COMPLETADA", "PENDIENTE"},
    ("dim_cliente", "tipo_cliente"): {"Mayorista", "Minorista", "Restaurante", "Tienda de barrio"},
    ("fct_devoluciones", "motivo"): {
        "Cliente desistió", "Empaque defectuoso", "Error de despacho", "Producto dañado", "Vencimiento cercano",
    },
    ("dim_producto", "activo"): {True, False},  # dominio booleano; en raw solo aparece true
}


def _nombres(pruebas):
    return {n for n, _ in pruebas}


@pytest.mark.parametrize("modelo,clave", sorted(CLAVES_SUSTITUTAS.items()))
def test_clave_sustituta_es_unique_y_not_null(modelo, clave):
    assert {"unique", "not_null"} <= _nombres(MARTS[modelo][clave])


@pytest.mark.parametrize("modelo,columna", sorted(FORANEAS))
def test_clave_foranea_tiene_relationships(modelo, columna):
    destino = FORANEAS[(modelo, columna)]
    rels = [a for n, a in MARTS[modelo].get(columna, []) if n == "relationships"]
    assert rels, f"{modelo}.{columna} sin prueba relationships"
    assert any(f"ref('{destino}')" in a.get("to", "") for a in rels)


@pytest.mark.parametrize("modelo,columna", sorted(CATEGORICAS))
def test_columna_categorica_tiene_accepted_values_reales(modelo, columna):
    avs = [a for n, a in MARTS[modelo].get(columna, []) if n == "accepted_values"]
    assert avs, f"{modelo}.{columna} sin accepted_values"
    assert set(avs[0]["values"]) == CATEGORICAS[(modelo, columna)]


def test_detalle_de_venta_tiene_relationships_hacia_venta():
    rels = [a for n, a in STAGING["stg_oltp__venta_detalle"]["id_venta"] if n == "relationships"]
    assert rels and "ref('stg_oltp__venta')" in rels[0]["to"] and rels[0]["field"] == "id_venta"


def _obligatorias_del_contrato():
    """{tabla_raw: [columnas]} con toda columna del contrato que no admite nulos."""
    ruta = os.path.join(RAIZ, "docs", "contrato_raw.md")
    tabla, resultado = None, {}
    with open(ruta, encoding="utf-8", errors="replace") as f:
        for linea in f:
            m = re.match(r"### Tabla `(\w+)`", linea)
            if m:
                tabla = m.group(1)
                resultado[tabla] = []
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if tabla and len(celdas) == 5 and celdas[0].startswith("`") and "Admite nulos" not in celdas[3]:
                resultado[tabla].append(celdas[0].strip("`"))
    return resultado


TABLAS_OLTP = {"sucursal", "categoria", "marca", "producto", "cliente", "venta", "venta_detalle"}


@pytest.mark.parametrize("tabla,columnas", sorted(_obligatorias_del_contrato().items()))
def test_columnas_obligatorias_tienen_not_null_en_staging(tabla, columnas):
    modelo = f"stg_{'oltp' if tabla in TABLAS_OLTP else 'archivos'}__{tabla}"
    faltan = [c for c in columnas if "not_null" not in _nombres(STAGING[modelo].get(c, []))]
    assert not faltan, f"{modelo}: sin not_null en {faltan}"


@pytest.mark.integracion
def test_linea_huerfana_llega_al_hecho_y_la_prueba_la_reporta(copia_raw):
    psql(
        "UPDATE raw_cierre.venta_detalle SET id_venta = '99999999' "
        "WHERE ctid = (SELECT min(ctid) FROM raw_cierre.venta_detalle);"
    )
    res_run = dbt("run", copia_raw)
    assert res_run.returncode == 0, resumen(res_run)
    assert escalar("SELECT count(*) FROM cierre_marts.fct_ventas_linea") == "3209"
    res_test = dbt("test", copia_raw)
    assert res_test.returncode != 0
    fallas = [l for l in res_test.stdout.splitlines() if "FAIL" in l and "relationships_stg_oltp__venta_detalle_id_venta" in l]
    assert fallas, "la prueba relationships de venta_detalle.id_venta debio fallar"
