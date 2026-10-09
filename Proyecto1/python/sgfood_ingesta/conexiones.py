"""Parámetros de conexión desde el entorno."""
from dataclasses import dataclass
import os
import psycopg

from sgfood_ingesta.errores import ConfiguracionInvalida


@dataclass(frozen=True)
class ParametrosConexion:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    def __repr__(self) -> str:
        return (
            f"ParametrosConexion(host={self.host!r}, port={self.port!r}, "
            f"dbname={self.dbname!r}, user={self.user!r}, password='***')"
        )

    def __str__(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.dbname}"


def _obtener_parametro(prefijo: str, nombre: str) -> str:
    var_name = f"{prefijo}_{nombre}"
    valor = os.environ.get(var_name)
    if valor is None or valor == "":
        raise ConfiguracionInvalida(f"Falta la variable de entorno obligatoria '{var_name}'")
    return valor


def _obtener_parametros(prefijo: str) -> ParametrosConexion:
    host = _obtener_parametro(prefijo, "HOST")
    port_str = _obtener_parametro(prefijo, "PORT")
    try:
        port = int(port_str)
    except ValueError:
        raise ConfiguracionInvalida(
            f"El puerto especificado en '{prefijo}_PORT' no es un entero valido: '{port_str}'"
        )
    dbname = _obtener_parametro(prefijo, "DB")
    user = _obtener_parametro(prefijo, "USER")
    password = _obtener_parametro(prefijo, "PASSWORD")

    return ParametrosConexion(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )


def obtener_parametros_dw() -> ParametrosConexion:
    """Obtiene los parámetros de conexión al DW desde variables DW_*."""
    return _obtener_parametros("DW")


def obtener_parametros_src() -> ParametrosConexion:
    """Obtiene los parámetros de conexión a la base fuente desde variables SRC_*."""
    return _obtener_parametros("SRC")


def conectar_dw() -> psycopg.Connection:
    """Abre conexión con el DW en modo transaccional (autocommit=False)."""
    params = obtener_parametros_dw()
    return psycopg.connect(
        host=params.host,
        port=params.port,
        dbname=params.dbname,
        user=params.user,
        password=params.password,
        autocommit=False,
    )


def conectar_src() -> psycopg.Connection:
    """Abre conexión con la fuente en modo solo lectura (read_only=True)."""
    params = obtener_parametros_src()
    conn = psycopg.connect(
        host=params.host,
        port=params.port,
        dbname=params.dbname,
        user=params.user,
        password=params.password,
        autocommit=False,
    )
    conn.read_only = True
    return conn
