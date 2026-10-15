"""R3: las conversiones de staging son tolerantes y las pruebas dbt reportan lo invalido."""
import pytest

from cierre_utils import copia_raw, dbt, escalar, psql, raw_intacto, resumen  # noqa: F401

pytestmark = pytest.mark.integracion


def test_valores_invalidos_no_detienen_dbt_run(copia_raw):
    psql(
        # fecha imposible en una venta
        "UPDATE raw_cierre.venta SET fecha = '2026-02-30' "
        "WHERE id_venta = (SELECT min(id_venta::bigint)::text FROM raw_cierre.venta);"
        # mes 13 en una meta
        "UPDATE raw_cierre.metas_ventas SET periodo = '2026-13' "
        "WHERE ctid = (SELECT min(ctid) FROM raw_cierre.metas_ventas);"
        # decimal fuera de rango de NUMERIC(5,4)
        "UPDATE raw_cierre.venta_detalle SET descuento = '12.5' "
        "WHERE ctid = (SELECT min(ctid) FROM raw_cierre.venta_detalle);"
        # entero de 12 digitos en una cantidad
        "UPDATE raw_cierre.venta_detalle SET cantidad = '123456789012' "
        "WHERE ctid = (SELECT max(ctid) FROM raw_cierre.venta_detalle);"
    )

    res_run = dbt("run", copia_raw)
    assert res_run.returncode == 0, f"dbt run debio terminar con 0:\n{resumen(res_run)}"

    # Los valores invalidos quedan en NULL
    assert escalar("SELECT count(*) FROM cierre_staging.stg_oltp__venta WHERE fecha IS NULL") == "1"
    assert escalar("SELECT count(*) FROM cierre_staging.stg_archivos__metas_ventas WHERE periodo IS NULL") == "1"
    assert escalar("SELECT count(*) FROM cierre_staging.stg_oltp__venta_detalle WHERE descuento IS NULL") != "0"
    assert escalar("SELECT count(*) FROM cierre_staging.stg_oltp__venta_detalle WHERE cantidad IS NULL") == "1"

    # dbt test reporta las columnas obligatorias afectadas
    res_test = dbt("test", copia_raw)
    assert res_test.returncode != 0, "dbt test debio fallar por las columnas obligatorias afectadas"
    salida = res_test.stdout
    for prueba in (
        "not_null_stg_oltp__venta_fecha",
        "not_null_stg_archivos__metas_ventas_periodo",
        "not_null_stg_oltp__venta_detalle_cantidad",
    ):
        lineas_falla = [l for l in salida.splitlines() if prueba in l and "FAIL" in l]
        assert lineas_falla, f"se esperaba falla de {prueba}"
