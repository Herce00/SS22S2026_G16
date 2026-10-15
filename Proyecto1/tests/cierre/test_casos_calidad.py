"""R9: los casos de calidad opcionales se cargan en una copia de raw y las pruebas dbt los detectan."""
import re

import pytest

from cierre_utils import (
    TOTAL_RAW_CONTRATO, _compose, conteos_marts, dbt, escalar, psql, raw_intacto, resumen, total_raw,
)  # noqa: F401

pytestmark = pytest.mark.integracion

CARGADOR = "/opt/airflow/sql/calidad/cargar_casos_calidad.py"
VARIABLES = {"schema_raw": "raw_calidad", "prefijo_schema": "cierre_"}

# caso (entidad.campo) -> prueba dbt que debe fallar por ese caso
ESPERADO = {
    "cliente.id_cliente": "not_null_stg_oltp__cliente_id_cliente",
    "producto.precio_lista": "not_null_stg_oltp__producto_precio_lista",
    "venta.id_cliente": "relationships_stg_oltp__venta_id_cliente",
    "venta_detalle.cantidad": "assert_ventas_cantidad_positiva",
    "venta_detalle.descuento": "assert_ventas_descuento_en_rango",
    "inventario.stock_disponible": "not_null_stg_archivos__inventario_bodega_stock_disponible",
    "inventario.fecha_vencimiento": "assert_inventario_vencimiento_posterior_al_corte",
    "proveedores_precios.costo_proveedor": "not_null_stg_archivos__proveedores_precios_costo_proveedor",
    "metas_ventas.meta_ventas": "assert_metas_positivas",
    "devoluciones.cantidad": "assert_devolucion_no_supera_venta",
}

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def huella_corrida_principal():
    return {
        "marts": conteos_marts(),
        "ventas": escalar("SELECT md5(string_agg(t::text, ',' ORDER BY t::text)) FROM marts.fct_ventas_linea t"),
        "clientes": escalar("SELECT md5(string_agg(t::text, ',' ORDER BY t::text)) FROM staging.stg_oltp__cliente t"),
    }


def test_casos_de_calidad_son_detectados_sin_afectar_la_corrida_principal(raw_intacto):
    antes = huella_corrida_principal()
    try:
        carga = _compose("exec", "-T", "airflow-scheduler", "python", CARGADOR)
        assert carga.returncode == 0, carga.stderr[-600:]
        aplicados = {l.split("\t")[1] for l in carga.stdout.splitlines() if l.startswith("APLICA")}
        assert set(ESPERADO) <= aplicados, f"casos sin aplicar: {set(ESPERADO) - aplicados}\n{carga.stdout}"

        res_run = dbt("run", VARIABLES)
        assert res_run.returncode == 0, resumen(res_run)

        res_test = dbt("test", VARIABLES)
        assert res_test.returncode != 0, "dbt test debio fallar con los casos de calidad cargados"
        fallidas = set(re.findall(r"FAIL\s+\d+\s+(\S+)", ANSI.sub("", res_test.stdout)))
        for caso, prueba in ESPERADO.items():
            assert any(f.startswith(prueba) for f in fallidas), f"{caso}: no fallo {prueba}; fallaron {sorted(fallidas)}"
        # raw_calidad es una copia: raw conserva el contrato
        assert total_raw() == TOTAL_RAW_CONTRATO
        assert huella_corrida_principal() == antes, "la corrida principal cambio"
    finally:
        limpieza = _compose("exec", "-T", "airflow-scheduler", "python", CARGADOR, "--limpiar")
        assert limpieza.returncode == 0, limpieza.stderr[-600:]
    esquemas = psql(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name IN ('raw_calidad', 'cierre_staging', 'cierre_marts')"
    )
    assert esquemas == []
