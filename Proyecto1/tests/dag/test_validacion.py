"""Pruebas del módulo de validación de sgfood_ingesta."""
import pytest
import subprocess
from conftest import run_docker_compose

# Importación condicional o directa para pruebas unitarias
try:
    from sgfood_ingesta.validacion import ConteoTabla, contar_fuentes_y_raw, validar_conteos
    from sgfood_ingesta.errores import ValidacionFallida
except ImportError:
    # Permitir que la prueba falle apropiadamente en rojo antes de que el módulo exista
    ConteoTabla = None
    contar_fuentes_y_raw = None
    validar_conteos = None
    ValidacionFallida = None


# --- Pruebas unitarias de validación de conteos ---

def test_validar_conteos_coinciden():
    assert validar_conteos is not None, "El módulo sgfood_ingesta.validacion aún no está implementado"
    conteos = [
        ConteoTabla(tabla_raw="sucursal", origen="oltp_sgfood.sucursal", filas_fuente=6, filas_raw=6),
        ConteoTabla(tabla_raw="empleado", origen="oltp_sgfood.empleado", filas_fuente=20, filas_raw=20),
    ]
    resultado = validar_conteos(conteos)
    assert len(resultado) == 2
    assert resultado[0].tabla_raw == "sucursal"
    assert resultado[1].tabla_raw == "empleado"


def test_validar_conteos_discrepancia_una_tabla():
    assert validar_conteos is not None and ValidacionFallida is not None
    conteos = [
        ConteoTabla(tabla_raw="promociones", origen="promociones.csv", filas_fuente=10, filas_raw=9),
    ]
    with pytest.raises(ValidacionFallida) as exc_info:
        validar_conteos(conteos)
    mensaje = str(exc_info.value)
    assert "promociones" in mensaje
    assert "10" in mensaje
    assert "9" in mensaje


def test_validar_conteos_discrepancia_dos_tablas():
    assert validar_conteos is not None and ValidacionFallida is not None
    conteos = [
        ConteoTabla(tabla_raw="canal_venta", origen="oltp_sgfood.canal_venta", filas_fuente=3, filas_raw=2),
        ConteoTabla(tabla_raw="cliente", origen="oltp_sgfood.cliente", filas_fuente=100, filas_raw=95),
    ]
    with pytest.raises(ValidacionFallida) as exc_info:
        validar_conteos(conteos)
    mensaje = str(exc_info.value)
    assert "canal_venta" in mensaje
    assert "cliente" in mensaje


# --- Prueba de integración en el contenedor ---

@pytest.mark.integracion
def test_validar_conteos_integracion_contenedor(proyecto1_dir):
    """Verifica validar_conteos en el contenedor sobre la carga completa y ante discrepancias."""
    # 1. Asegurar que raw está cargado y ejecutar validar_conteos
    cmd_ok = [
        "exec", "-T", "airflow-scheduler", "python", "-c",
        (
            "import logging\n"
            "logging.basicConfig(level=logging.INFO)\n"
            "from sgfood_ingesta.validacion import validar_conteos\n"
            "res = validar_conteos()\n"
            "print(f'TABLAS={len(res)} TOTAL={sum(r.filas_raw for r in res)}')\n"
        )
    ]
    res_ok = run_docker_compose(*cmd_ok, cwd=proyecto1_dir)
    assert res_ok.returncode == 0, f"validar_conteos falló en el contenedor:\n{res_ok.stdout}\n{res_ok.stderr}"
    assert "TABLAS=12" in res_ok.stdout
    assert "TOTAL=8864" in res_ok.stdout

    # 2. Borrar una fila de raw.promociones y verificar que falla nombrando promociones
    try:
        res_del = run_docker_compose(
            "exec", "-T", "dw", "psql", "-U", "dw_user", "-d", "sgfood_dw", "-c",
            "DELETE FROM raw.promociones WHERE ctid IN (SELECT ctid FROM raw.promociones LIMIT 1);",
            cwd=proyecto1_dir
        )
        assert res_del.returncode == 0, f"Fallo al borrar fila de prueba: {res_del.stderr}"

        # Ejecutar validar_conteos: debe fallar con código no cero y mencionar promociones
        cmd_falla = [
            "exec", "-T", "airflow-scheduler", "python", "-c",
            "from sgfood_ingesta.validacion import validar_conteos; validar_conteos()"
        ]
        res_falla = run_docker_compose(*cmd_falla, cwd=proyecto1_dir)
        assert res_falla.returncode != 0, "validar_conteos debió fallar tras alterar raw.promociones"
        salida_error = res_falla.stdout + "\n" + res_falla.stderr
        assert "promociones" in salida_error, f"El error no nombra 'promociones':\n{salida_error}"

    finally:
        # 3. Restaurar raw.promociones recargando la fuente
        run_docker_compose(
            "exec", "-T", "airflow-scheduler", "python", "-c",
            "from sgfood_ingesta.ingesta import cargar_fuente; cargar_fuente('promociones')",
            cwd=proyecto1_dir
        )
