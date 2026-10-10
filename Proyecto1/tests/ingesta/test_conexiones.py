"""Pruebas unitarias de parámetros de conexión y configuración desde el entorno."""
import pytest

from sgfood_ingesta.conexiones import (
    ParametrosConexion,
    obtener_parametros_dw,
    obtener_parametros_src,
)
from sgfood_ingesta.errores import ConfiguracionInvalida


def test_parametros_dw_desde_entorno(monkeypatch):
    """Arma los parámetros de DW leyendo variables de entorno DW_*."""
    monkeypatch.setenv("DW_HOST", "dw.host.local")
    monkeypatch.setenv("DW_PORT", "5432")
    monkeypatch.setenv("DW_DB", "sgfood_dw")
    monkeypatch.setenv("DW_USER", "usuario_dw")
    monkeypatch.setenv("DW_PASSWORD", "secreto_dw_123")

    params = obtener_parametros_dw()
    assert isinstance(params, ParametrosConexion)
    assert params.host == "dw.host.local"
    assert params.port == 5432
    assert params.dbname == "sgfood_dw"
    assert params.user == "usuario_dw"
    assert params.password == "secreto_dw_123"


def test_parametros_src_desde_entorno(monkeypatch):
    """Arma los parámetros de SRC leyendo variables de entorno SRC_*."""
    monkeypatch.setenv("SRC_HOST", "src.host.local")
    monkeypatch.setenv("SRC_PORT", "5433")
    monkeypatch.setenv("SRC_DB", "sgfood_src")
    monkeypatch.setenv("SRC_USER", "usuario_src")
    monkeypatch.setenv("SRC_PASSWORD", "secreto_src_456")

    params = obtener_parametros_src()
    assert isinstance(params, ParametrosConexion)
    assert params.host == "src.host.local"
    assert params.port == 5433
    assert params.dbname == "sgfood_src"
    assert params.user == "usuario_src"
    assert params.password == "secreto_src_456"


@pytest.mark.parametrize(
    "var_faltante",
    ["DW_HOST", "DW_PORT", "DW_DB", "DW_USER", "DW_PASSWORD"],
)
def test_variable_faltante_dw_lanza_configuracion_invalida(monkeypatch, var_faltante):
    """Si falta alguna variable DW_*, lanza ConfiguracionInvalida nombrando la variable."""
    env_completo = {
        "DW_HOST": "localhost",
        "DW_PORT": "5432",
        "DW_DB": "sgfood_dw",
        "DW_USER": "postgres",
        "DW_PASSWORD": "password",
    }
    for k, v in env_completo.items():
        monkeypatch.setenv(k, v)

    monkeypatch.delenv(var_faltante, raising=False)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        obtener_parametros_dw()

    assert var_faltante in str(exc_info.value)


@pytest.mark.parametrize(
    "var_faltante",
    ["SRC_HOST", "SRC_PORT", "SRC_DB", "SRC_USER", "SRC_PASSWORD"],
)
def test_variable_faltante_src_lanza_configuracion_invalida(monkeypatch, var_faltante):
    """Si falta alguna variable SRC_*, lanza ConfiguracionInvalida nombrando la variable."""
    env_completo = {
        "SRC_HOST": "localhost",
        "SRC_PORT": "5432",
        "SRC_DB": "sgfood_src",
        "SRC_USER": "postgres",
        "SRC_PASSWORD": "password",
    }
    for k, v in env_completo.items():
        monkeypatch.setenv(k, v)

    monkeypatch.delenv(var_faltante, raising=False)

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        obtener_parametros_src()

    assert var_faltante in str(exc_info.value)


def test_representacion_no_incluye_password(monkeypatch):
    """str() y repr() de ParametrosConexion no deben exponer la contraseña."""
    password_secreto = "secreto_super_confidencial_xyz999"
    monkeypatch.setenv("DW_HOST", "localhost")
    monkeypatch.setenv("DW_PORT", "5432")
    monkeypatch.setenv("DW_DB", "sgfood_dw")
    monkeypatch.setenv("DW_USER", "postgres")
    monkeypatch.setenv("DW_PASSWORD", password_secreto)

    params = obtener_parametros_dw()
    repr_str = repr(params)
    str_str = str(params)

    assert password_secreto not in repr_str
    assert password_secreto not in str_str
    assert "password" in repr_str.lower()
    assert "***" in repr_str or "oculta" in repr_str.lower() or "redacted" in repr_str.lower()


def test_puerto_invalido_lanza_configuracion_invalida(monkeypatch):
    """Un puerto que no sea entero lanza ConfiguracionInvalida nombrando el puerto."""
    monkeypatch.setenv("DW_HOST", "localhost")
    monkeypatch.setenv("DW_PORT", "no_es_un_puerto")
    monkeypatch.setenv("DW_DB", "sgfood_dw")
    monkeypatch.setenv("DW_USER", "postgres")
    monkeypatch.setenv("DW_PASSWORD", "secret")

    with pytest.raises(ConfiguracionInvalida) as exc_info:
        obtener_parametros_dw()

    assert "DW_PORT" in str(exc_info.value)
