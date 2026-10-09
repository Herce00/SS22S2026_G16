import os
import pytest


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
