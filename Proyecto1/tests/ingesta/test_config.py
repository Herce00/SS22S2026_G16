from dataclasses import FrozenInstanceError
import os
import pytest
import yaml

from sgfood_ingesta.config import Fuente, cargar_configuracion
from sgfood_ingesta.errores import ConfiguracionInvalida


def test_requirements_excludes_pandas(proyecto1_dir):
    """Verifica estaticamente que airflow/requirements.txt no incluya pandas."""
    req_path = os.path.join(proyecto1_dir, "airflow", "requirements.txt")
    assert os.path.isfile(req_path), f"requirements.txt no existe en {req_path}"

    with open(req_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "pandas" not in content.lower(), (
        "airflow/requirements.txt no debe incluir pandas (decision I2)"
    )


def test_sgfood_ingesta_public_interface():
    """Verifica que el paquete sgfood_ingesta exponga la interfaz publica requerida."""
    import sgfood_ingesta

    assert hasattr(sgfood_ingesta, "listar_fuentes"), "sgfood_ingesta debe exponer listar_fuentes"
    assert callable(sgfood_ingesta.listar_fuentes), "listar_fuentes debe ser invocable"

    assert hasattr(sgfood_ingesta, "cargar_fuente"), "sgfood_ingesta debe exponer cargar_fuente"
    assert callable(sgfood_ingesta.cargar_fuente), "cargar_fuente debe ser invocable"

    assert hasattr(sgfood_ingesta, "cargar_todas"), "sgfood_ingesta debe exponer cargar_todas"
    assert callable(sgfood_ingesta.cargar_todas), "cargar_todas debe ser invocable"


def test_cargar_configuracion_real(proyecto1_dir):
    """Con el fuentes.yml real, devuelve 12 objetos Fuente en el orden declarado."""
    real_path = os.path.join(proyecto1_dir, "python", "config", "fuentes.yml")
    fuentes = cargar_configuracion(real_path)

    assert isinstance(fuentes, list), "cargar_configuracion debe devolver una lista"
    assert len(fuentes) == 12, f"Se esperaban 12 fuentes, se obtuvieron {len(fuentes)}"

    # Verificar primer y ultimo elemento para confirmar orden
    assert fuentes[0].tabla_raw == "sucursal"
    assert fuentes[0].tipo == "postgres"
    assert fuentes[0].origen == "oltp_sgfood.sucursal"
    assert "id_sucursal" in fuentes[0].columnas

    assert fuentes[-1].tabla_raw == "promociones"
    assert fuentes[-1].tipo == "csv"
    assert fuentes[-1].origen == "promociones.csv"


def test_cargar_configuracion_inexistente():
    """Archivo inexistente produce ConfiguracionInvalida."""
    with pytest.raises(ConfiguracionInvalida, match="no existe"):
        cargar_configuracion("/ruta/inexistente/fuentes.yml")


def test_cargar_configuracion_env_override(proyecto1_dir, monkeypatch):
    """La ruta se toma de SGFOOD_FUENTES_PATH cuando esta definida en el entorno."""
    real_path = os.path.join(proyecto1_dir, "python", "config", "fuentes.yml")
    monkeypatch.setenv("SGFOOD_FUENTES_PATH", real_path)

    fuentes = cargar_configuracion()
    assert len(fuentes) == 12


def test_fuente_es_inmutable():
    """Fuente es un dataclass inmutable (frozen)."""
    f = Fuente(
        tabla_raw="test",
        tipo="csv",
        origen="test.csv",
        columnas=("c1", "c2"),
    )
    with pytest.raises(FrozenInstanceError):
        f.tabla_raw = "otro"  # type: ignore


@pytest.mark.parametrize(
    "invalid_data, error_match",
    [
        ({"fuentes": []}, "version"),
        ({"version": 2, "fuentes": []}, "version"),
        ({"version": 1, "fuentes": "no_es_lista"}, "fuentes"),
        (
            {"version": 1, "fuentes": [{"tipo": "csv", "origen": "a.csv", "columnas": ["c1"]}]},
            "tabla_raw",
        ),
        (
            {
                "version": 1,
                "fuentes": [{"tabla_raw": "t", "tipo": "mysql", "origen": "a", "columnas": ["c1"]}],
            },
            "tipo",
        ),
        (
            {
                "version": 1,
                "fuentes": [
                    {"tabla_raw": "t", "tipo": "csv", "origen": "a.csv", "columnas": ["c1"]},
                    {"tabla_raw": "t", "tipo": "csv", "origen": "b.csv", "columnas": ["c2"]},
                ],
            },
            "duplicad",
        ),
        (
            {
                "version": 1,
                "fuentes": [{"tabla_raw": "t", "tipo": "csv", "origen": "a.csv", "columnas": []}],
            },
            "columnas",
        ),
        (
            {
                "version": 1,
                "fuentes": [
                    {"tabla_raw": "t", "tipo": "csv", "origen": "a.csv", "columnas": ["c1", "c1"]}
                ],
            },
            "columnas duplicad",
        ),
        (
            {
                "version": 1,
                "fuentes": [
                    {"tabla_raw": "t", "tipo": "postgres", "origen": "sin_schema", "columnas": ["c1"]}
                ],
            },
            "schema",
        ),
    ],
)
def test_cargar_configuracion_invalida(tmp_path, invalid_data, error_match):
    """Produce ConfiguracionInvalida ante cualquier defecto de estructura o tipos."""
    invalid_file = tmp_path / "fuentes_invalido.yml"
    with open(invalid_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(invalid_data, f)

    with pytest.raises(ConfiguracionInvalida, match=error_match):
        cargar_configuracion(str(invalid_file))
