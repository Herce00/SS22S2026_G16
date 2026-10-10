import os
import subprocess
import pytest

OFFICIAL_FILES = [
    "casos_calidad_opcionales.csv",
    "catalogo_insumos_sgfood.xlsx",
    "devoluciones.csv",
    "inventario_bodega.csv",
    "metas_ventas.csv",
    "promociones.csv",
    "proveedores_precios.csv",
    "sgfood_oltp.sql",
]

EXPECTED_CSV_ROWS = {
    "inventario_bodega.csv": 3840,
    "proveedores_precios.csv": 103,
    "devoluciones.csv": 80,
    "metas_ventas.csv": 48,
    "promociones.csv": 30,
    "casos_calidad_opcionales.csv": 10,
}

UTF8_BOM = b"\xef\xbb\xbf"


def test_official_files_exist(proyecto1_dir):
    """Verifica que existan exactamente los 8 archivos oficiales en data/."""
    data_dir = os.path.join(proyecto1_dir, "data")
    assert os.path.isdir(data_dir), f"El directorio {data_dir} no existe"

    for filename in OFFICIAL_FILES:
        filepath = os.path.join(data_dir, filename)
        assert os.path.isfile(filepath), f"El archivo oficial {filename} no existe en {data_dir}"


def test_csv_encoding_and_line_endings(proyecto1_dir):
    """Verifica que cada CSV comience con BOM UTF-8 y use terminaciones CRLF."""
    data_dir = os.path.join(proyecto1_dir, "data")
    csv_files = [f for f in OFFICIAL_FILES if f.endswith(".csv")]

    for filename in csv_files:
        filepath = os.path.join(data_dir, filename)
        with open(filepath, "rb") as f:
            content = f.read()

        assert content.startswith(UTF8_BOM), (
            f"{filename} no comienza con BOM UTF-8 (\\xef\\xbb\\xbf)"
        )
        assert b"\r\n" in content, (
            f"{filename} no utiliza finales de linea CRLF (\\r\\n)"
        )


def test_csv_row_counts(proyecto1_dir):
    """Verifica que cada CSV tenga la cantidad exacta de filas de datos."""
    data_dir = os.path.join(proyecto1_dir, "data")

    for filename, expected_rows in EXPECTED_CSV_ROWS.items():
        filepath = os.path.join(data_dir, filename)
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            lines = [line for line in f.read().split("\r\n") if line]

        # Primera linea es encabezado, las restantes son filas de datos
        header = lines[0]
        data_rows = len(lines) - 1
        assert data_rows == expected_rows, (
            f"{filename}: se esperaban {expected_rows} filas de datos, pero se encontraron {data_rows}"
        )


def test_gitattributes_unset_for_data_files(proyecto1_dir):
    """Verifica que git check-attr text reporte 'unset' para los archivos de data/."""
    for filename in OFFICIAL_FILES:
        rel_path = f"data/{filename}"
        cmd = ["git", "check-attr", "text", rel_path]
        result = subprocess.run(cmd, cwd=proyecto1_dir, capture_output=True, text=True)

        assert result.returncode == 0, f"Error ejecutando git check-attr: {result.stderr}"
        output = result.stdout.strip()
        assert ": text: unset" in output, (
            f"git check-attr text para {rel_path} no retorno 'unset'. Salida: {output}"
        )
