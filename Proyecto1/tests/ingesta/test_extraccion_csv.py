import os
import pytest

from sgfood_ingesta.config import cargar_configuracion
from sgfood_ingesta.errores import EncabezadoInvalido, FilaInvalida
from sgfood_ingesta.extraccion import extraer_filas_csv


@pytest.fixture
def fixtures_dir(proyecto1_dir):
    return os.path.join(proyecto1_dir, "tests", "ingesta", "fixtures")


def test_extraccion_csv_valido_y_bom(fixtures_dir):
    """Verifica extraccion de CSV con BOM, preservacion de tipos en texto, campos vacios a None, comas entrecomilladas y espacios."""
    csv_path = os.path.join(fixtures_dir, "valido.csv")
    columnas = ("id", "codigo", "monto", "nota")

    filas = list(extraer_filas_csv(csv_path, columnas))

    # Debe haber exactamente 4 filas de datos (la linea en blanco se omite)
    assert len(filas) == 4

    # Fila 1: tipos en texto sin conversion
    assert filas[0] == ("1", "007", "1.50", "hola")

    # Fila 2: campos vacios convertidos a None
    assert filas[1] == ("2", "008", None, None)

    # Fila 3: campo con solo espacios conserva los espacios
    assert filas[2] == ("3", "009", "2.00", "   ")

    # Fila 4: campo entre comillas con coma se lee como un solo valor
    assert filas[3] == ("4", "010", "3.00", "campo, con coma")


def test_extraccion_csv_encabezado_invalido(fixtures_dir):
    """Encabezado distinto o en otro orden produce EncabezadoInvalido."""
    csv_path = os.path.join(fixtures_dir, "encabezado_malo.csv")
    columnas_esperadas = ("id", "codigo", "monto", "nota")

    with pytest.raises(EncabezadoInvalido):
        list(extraer_filas_csv(csv_path, columnas_esperadas))


def test_extraccion_csv_fila_corta(fixtures_dir):
    """Fila con campo de menos produce FilaInvalida con el numero de linea (linea 3 en el archivo)."""
    csv_path = os.path.join(fixtures_dir, "fila_corta.csv")
    columnas = ("id", "codigo", "monto", "nota")

    with pytest.raises(FilaInvalida) as exc_info:
        list(extraer_filas_csv(csv_path, columnas))

    assert exc_info.value.linea == 3, f"Se esperaba linea 3, se obtuvo {exc_info.value.linea}"


def test_extraccion_csv_fila_larga(fixtures_dir):
    """Fila con campo de mas produce FilaInvalida con el numero de linea (linea 3 en el archivo)."""
    csv_path = os.path.join(fixtures_dir, "fila_larga.csv")
    columnas = ("id", "codigo", "monto", "nota")

    with pytest.raises(FilaInvalida) as exc_info:
        list(extraer_filas_csv(csv_path, columnas))

    assert exc_info.value.linea == 3, f"Se esperaba linea 3, se obtuvo {exc_info.value.linea}"


def test_extraccion_csv_reales(proyecto1_dir):
    """Con cada CSV real de data/, la cantidad de filas coincide con la del contrato."""
    config_path = os.path.join(proyecto1_dir, "python", "config", "fuentes.yml")
    fuentes = cargar_configuracion(config_path)
    csv_fuentes = [f for f in fuentes if f.tipo == "csv"]

    conteos_esperados = {
        "inventario_bodega": 3840,
        "proveedores_precios": 103,
        "devoluciones": 80,
        "metas_ventas": 48,
        "promociones": 30,
    }

    data_dir = os.path.join(proyecto1_dir, "data")

    for f in csv_fuentes:
        csv_path = os.path.join(data_dir, f.origen)
        filas = list(extraer_filas_csv(csv_path, f.columnas))
        esperado = conteos_esperados[f.tabla_raw]
        assert len(filas) == esperado, (
            f"Conteo incorrecto para {f.tabla_raw}: obtenido {len(filas)}, esperado {esperado}"
        )
