import csv
import os
import re
import pytest
import yaml

SNAKE_CASE_REGEX = re.compile(r"^[a-z][a-z0-9_]*$")
FORBIDDEN_AUDIT_COLUMNS = {"_loaded_at", "_source"}
SENSITIVE_KEYWORDS = ["password", "secret", "token", "host:", "port:", "dbname:"]


@pytest.fixture(scope="module")
def fuentes_config(proyecto1_dir):
    """Carga y valida el archivo fuentes.yml."""
    config_path = os.path.join(proyecto1_dir, "python", "config", "fuentes.yml")
    assert os.path.isfile(config_path), f"El archivo de configuracion no existe en {config_path}"

    with open(config_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # Validar que no contenga credenciales, hosts ni rutas absolutas
    lower_content = raw_content.lower()
    for kw in SENSITIVE_KEYWORDS:
        assert kw not in lower_content, f"El archivo fuentes.yml no debe contener '{kw}'"

    assert "c:\\" not in lower_content and "c:/" not in lower_content, (
        "El archivo fuentes.yml contiene rutas absolutas de Windows"
    )
    assert not re.search(r"/(?:home|etc|var|tmp|Users)/", raw_content), (
        "El archivo fuentes.yml contiene rutas absolutas de sistema"
    )

    data = yaml.safe_load(raw_content)
    assert isinstance(data, dict), "El archivo fuentes.yml debe ser un mapeo YAML valido"
    return data


def test_fuentes_config_version(fuentes_config):
    """Verifica que el archivo declare version: 1."""
    assert fuentes_config.get("version") == 1, "La clave 'version' debe ser igual a 1"


def test_fuentes_config_counts_and_types(fuentes_config):
    """Verifica exactamente 12 fuentes: 7 de postgres y 5 de csv."""
    fuentes = fuentes_config.get("fuentes", [])
    assert isinstance(fuentes, list), "'fuentes' debe ser una lista"
    assert len(fuentes) == 12, f"Se esperaban exactamente 12 fuentes, se encontraron {len(fuentes)}"

    postgres_fuentes = [f for f in fuentes if f.get("tipo") == "postgres"]
    csv_fuentes = [f for f in fuentes if f.get("tipo") == "csv"]

    assert len(postgres_fuentes) == 7, (
        f"Se esperaban 7 fuentes tipo postgres, se encontraron {len(postgres_fuentes)}"
    )
    assert len(csv_fuentes) == 5, (
        f"Se esperaban 5 fuentes tipo csv, se encontraron {len(csv_fuentes)}"
    )


def test_fuentes_config_tabla_raw_unique_snake_case(fuentes_config):
    """Verifica que cada tabla_raw sea unica y este en snake_case."""
    fuentes = fuentes_config.get("fuentes", [])
    tablas_raw = [f.get("tabla_raw") for f in fuentes]

    assert len(tablas_raw) == len(set(tablas_raw)), (
        f"Hay nombres de tabla_raw duplicados: {tablas_raw}"
    )

    for tabla in tablas_raw:
        assert isinstance(tabla, str), f"tabla_raw debe ser una cadena: {tabla}"
        assert SNAKE_CASE_REGEX.match(tabla), (
            f"tabla_raw '{tabla}' no cumple con el formato snake_case"
        )


def test_fuentes_config_origen_valid(fuentes_config, proyecto1_dir):
    """Verifica que cada origen exista o cumpla con el formato calificado esperado."""
    fuentes = fuentes_config.get("fuentes", [])
    data_dir = os.path.join(proyecto1_dir, "data")

    for f in fuentes:
        tipo = f.get("tipo")
        origen = f.get("origen")
        tabla = f.get("tabla_raw")

        assert isinstance(origen, str), f"El origen para {tabla} debe ser una cadena"

        if tipo == "csv":
            assert origen != "casos_calidad_opcionales.csv", (
                "casos_calidad_opcionales.csv no debe declararse como fuente"
            )
            csv_path = os.path.join(data_dir, origen)
            assert os.path.isfile(csv_path), (
                f"El archivo origen CSV '{origen}' para la tabla '{tabla}' no existe en {data_dir}"
            )
        elif tipo == "postgres":
            assert origen.startswith("oltp_sgfood."), (
                f"El origen postgres '{origen}' para la tabla '{tabla}' debe pertenecer al schema 'oltp_sgfood.'"
            )
            tabla_src = origen.split(".", 1)[1]
            assert SNAKE_CASE_REGEX.match(tabla_src), (
                f"El nombre de tabla fuente '{tabla_src}' no cumple snake_case"
            )
        else:
            pytest.fail(f"Tipo de fuente desconocido '{tipo}' para tabla '{tabla}'")


def test_fuentes_config_csv_columns_match_headers(fuentes_config, proyecto1_dir):
    """Verifica que las columnas de fuentes CSV coincidan en nombre y orden con los encabezados leidos como utf-8-sig."""
    fuentes = fuentes_config.get("fuentes", [])
    data_dir = os.path.join(proyecto1_dir, "data")
    csv_fuentes = [f for f in fuentes if f.get("tipo") == "csv"]

    for f in csv_fuentes:
        origen = f.get("origen")
        declared_cols = f.get("columnas", [])
        tabla = f.get("tabla_raw")

        csv_path = os.path.join(data_dir, origen)
        with open(csv_path, "r", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)
            actual_header = next(reader)

        assert declared_cols == actual_header, (
            f"Discrepancia en columnas para tabla '{tabla}' (origen '{origen}'):\n"
            f"Declaradas: {declared_cols}\n"
            f"Encabezado real: {actual_header}"
        )


def test_fuentes_config_no_duplicate_or_audit_columns(fuentes_config):
    """Verifica que ninguna lista de columnas tenga duplicados ni incluya columnas de auditoria."""
    fuentes = fuentes_config.get("fuentes", [])

    for f in fuentes:
        tabla = f.get("tabla_raw")
        columnas = f.get("columnas", [])

        assert isinstance(columnas, list) and len(columnas) > 0, (
            f"La tabla '{tabla}' no tiene columnas declaradas"
        )
        assert len(columnas) == len(set(columnas)), (
            f"La tabla '{tabla}' tiene columnas duplicadas: {columnas}"
        )

        for col in columnas:
            assert col not in FORBIDDEN_AUDIT_COLUMNS, (
                f"La tabla '{tabla}' incluye la columna de auditoria '{col}' en su lista de negocio"
            )
            assert SNAKE_CASE_REGEX.match(col), (
                f"La columna '{col}' de la tabla '{tabla}' no cumple con snake_case"
            )


def test_fuentes_config_casos_calidad_not_declared(fuentes_config):
    """Verifica explicitamente que casos_calidad_opcionales.csv no aparezca en ninguna fuente."""
    fuentes = fuentes_config.get("fuentes", [])
    for f in fuentes:
        assert f.get("origen") != "casos_calidad_opcionales.csv", (
            "casos_calidad_opcionales.csv no debe declararse como fuente"
        )
        assert "casos_calidad" not in f.get("tabla_raw", ""), (
            "No debe existir una tabla raw para casos_calidad"
        )
