"""Pruebas unitarias del manejo de errores de la línea de comandos."""
import logging

from sgfood_ingesta import cli
from sgfood_ingesta.errores import ErrorIngesta


def test_fallo_inesperado_registra_la_traza(monkeypatch, caplog):
    """Un error no previsto termina con código 1 y deja la traza completa en el registro."""

    def carga_que_falla():
        raise RuntimeError("conexion rechazada")

    monkeypatch.setattr(cli, "cargar_todas", carga_que_falla)

    with caplog.at_level(logging.ERROR, logger="sgfood_ingesta.cli"):
        codigo = cli.main([])

    assert codigo == 1
    registros = [r for r in caplog.records if r.name == "sgfood_ingesta.cli"]
    assert len(registros) == 1
    assert registros[0].exc_info is not None
    assert registros[0].exc_info[0] is RuntimeError


def test_error_de_ingesta_se_registra_sin_traza(monkeypatch, caplog):
    """Un error propio de la ingesta termina con código 1 y registra solo su mensaje."""

    def carga_que_falla():
        raise ErrorIngesta("El archivo CSV no existe")

    monkeypatch.setattr(cli, "cargar_todas", carga_que_falla)

    with caplog.at_level(logging.ERROR, logger="sgfood_ingesta.cli"):
        codigo = cli.main([])

    assert codigo == 1
    registros = [r for r in caplog.records if r.name == "sgfood_ingesta.cli"]
    assert len(registros) == 1
    assert "El archivo CSV no existe" in registros[0].getMessage()
    assert registros[0].exc_info is None
