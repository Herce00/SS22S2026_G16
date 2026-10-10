import os
import re
import pytest
import yaml

EXPECTED_ROW_COUNTS = {
    "sucursal": 6,
    "categoria": 8,
    "marca": 10,
    "producto": 80,
    "cliente": 250,
    "venta": 1200,
    "venta_detalle": 3209,
    "inventario_bodega": 3840,
    "proveedores_precios": 103,
    "devoluciones": 80,
    "metas_ventas": 48,
    "promociones": 30,
}


@pytest.fixture(scope="module")
def fuentes_data(proyecto1_dir):
    config_path = os.path.join(proyecto1_dir, "python", "config", "fuentes.yml")
    assert os.path.isfile(config_path), f"fuentes.yml no existe en {config_path}"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def contrato_content(proyecto1_dir):
    doc_path = os.path.join(proyecto1_dir, "docs", "contrato_raw.md")
    assert os.path.isfile(doc_path), f"contrato_raw.md no existe en {doc_path}"
    with open(doc_path, "r", encoding="utf-8") as f:
        return f.read()


def test_contrato_version_matches_fuentes(fuentes_data, contrato_content):
    """Verifica que el documento declare la misma version que fuentes.yml."""
    version_expected = fuentes_data.get("version", 1)
    # Buscar patron como 'v1', 'Versión: 1', 'Versión 1', etc.
    match = re.search(r"[Vv]ersi[oó]n[:\s]+v?(\d+)", contrato_content)
    assert match is not None, "El documento contrato_raw.md no especifica version"
    doc_version = int(match.group(1))
    assert doc_version == version_expected, (
        f"Version del documento ({doc_version}) no coincide con fuentes.yml ({version_expected})"
    )


def test_contrato_mentions_all_tables_and_columns(fuentes_data, contrato_content):
    """Verifica que el documento mencione cada tabla_raw y cada columna declarada en fuentes.yml."""
    fuentes = fuentes_data.get("fuentes", [])

    for f in fuentes:
        tabla = f.get("tabla_raw")
        assert f"`{tabla}`" in contrato_content or f"### {tabla}" in contrato_content or f"## {tabla}" in contrato_content, (
            f"El documento no menciona la tabla raw '{tabla}'"
        )

        for col in f.get("columnas", []):
            assert f"`{col}`" in contrato_content or col in contrato_content, (
                f"El documento no menciona la columna '{col}' de la tabla '{tabla}'"
            )


def test_contrato_has_no_undeclared_table_sections(fuentes_data, contrato_content):
    """Verifica que no existan secciones de tablas en el documento que no esten en fuentes.yml."""
    expected_tables = set(f.get("tabla_raw") for f in fuentes_data.get("fuentes", []))

    # Detectar encabezados de nivel 3 o 4 para tablas individuales
    headers = re.findall(r"^#{3,4}\s+(?:Tabla\s+)?`?([a-z0-9_]+)`?", contrato_content, re.MULTILINE)
    # Filtrar posibles encabezados que no sean tablas
    table_headers = [h for h in headers if h in expected_tables or "_" in h]

    for th in table_headers:
        assert th in expected_tables, (
            f"El documento contiene una seccion para una tabla no declarada en fuentes.yml: '{th}'"
        )


def test_contrato_row_counts_match(contrato_content):
    """Verifica que los conteos de filas del documento coincidan con los esperados por las pruebas."""
    for tabla, expected_rows in EXPECTED_ROW_COUNTS.items():
        # Buscar en la tabla de resumen la fila que contenga el nombre de la tabla y la cantidad
        pattern = rf"`{tabla}`.*?[|].*?[|].*?[|].*?[|]\s*(\d[\d\.\,]*)\s*[|]"
        match = re.search(pattern, contrato_content)
        if not match:
            # Buscar patron alternativo: tabla y numero de filas
            pattern = rf"`?{tabla}`?.*?(\d[\d\.\,]+)\s*(?:filas|registros)"
            match = re.search(pattern, contrato_content, re.IGNORECASE)

        assert match is not None, (
            f"No se encontro el conteo de filas para la tabla '{tabla}' en contrato_raw.md"
        )
        count_found = int(match.group(1).replace(".", "").replace(",", ""))
        assert count_found == expected_rows, (
            f"Conteo de filas para '{tabla}' en contrato_raw.md ({count_found}) no coincide con el esperado ({expected_rows})"
        )
