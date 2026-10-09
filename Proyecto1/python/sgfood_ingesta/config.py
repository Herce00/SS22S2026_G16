"""Lectura y validación de fuentes.yml."""
from dataclasses import dataclass
import os
from typing import Literal
import yaml

from sgfood_ingesta.errores import ConfiguracionInvalida

DEFAULT_CONFIG_PATH = "/opt/airflow/python/config/fuentes.yml"


@dataclass(frozen=True)
class Fuente:
    tabla_raw: str
    tipo: Literal["postgres", "csv"]
    origen: str
    columnas: tuple[str, ...]


def obtener_ruta_configuracion(ruta: str | None = None) -> str:
    """Resuelve la ruta del archivo fuentes.yml."""
    if ruta:
        return ruta
    env_path = os.environ.get("SGFOOD_FUENTES_PATH")
    if env_path:
        return env_path
    if os.path.isfile(DEFAULT_CONFIG_PATH):
        return DEFAULT_CONFIG_PATH
    # Fallback relativo al paquete en desarrollo
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback_path = os.path.join(base_dir, "config", "fuentes.yml")
    return fallback_path


def cargar_configuracion(ruta: str | None = None) -> list[Fuente]:
    """Carga y valida el archivo fuentes.yml, retornando la lista ordenada de objetos Fuente."""
    config_file = obtener_ruta_configuracion(ruta)

    if not os.path.isfile(config_file):
        raise ConfiguracionInvalida(f"El archivo de configuracion no existe: '{config_file}'")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        raise ConfiguracionInvalida(f"Error parseando fuentes.yml: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfiguracionInvalida("fuentes.yml debe ser un mapeo YAML valido")

    if data.get("version") != 1:
        raise ConfiguracionInvalida(f"Se requiere version: 1 en fuentes.yml, encontrado: {data.get('version')}")

    fuentes_raw = data.get("fuentes")
    if not isinstance(fuentes_raw, list):
        raise ConfiguracionInvalida("'fuentes' debe ser una lista en fuentes.yml")

    fuentes: list[Fuente] = []
    tablas_vistas: set[str] = set()

    for item in fuentes_raw:
        if not isinstance(item, dict):
            raise ConfiguracionInvalida("Cada elemento de 'fuentes' debe ser un diccionario")

        for campo in ("tabla_raw", "tipo", "origen", "columnas"):
            if campo not in item:
                raise ConfiguracionInvalida(f"Falta el campo obligatorio '{campo}' en la fuente")

        tabla_raw = item["tabla_raw"]
        tipo = item["tipo"]
        origen = item["origen"]
        columnas = item["columnas"]

        if not isinstance(tabla_raw, str) or not tabla_raw:
            raise ConfiguracionInvalida("tabla_raw debe ser una cadena no vacia")

        if tabla_raw in tablas_vistas:
            raise ConfiguracionInvalida(f"Nombre de tabla_raw duplicado: '{tabla_raw}'")
        tablas_vistas.add(tabla_raw)

        if tipo not in ("postgres", "csv"):
            raise ConfiguracionInvalida(f"tipo desconocido '{tipo}' para tabla '{tabla_raw}'. Debe ser postgres o csv")

        if not isinstance(origen, str) or not origen:
            raise ConfiguracionInvalida(f"origen invalido para tabla '{tabla_raw}'")

        if tipo == "postgres" and "." not in origen:
            raise ConfiguracionInvalida(f"Origen postgres '{origen}' debe incluir schema (ej. schema.tabla)")

        if not isinstance(columnas, list) or len(columnas) == 0:
            raise ConfiguracionInvalida(f"columnas para '{tabla_raw}' debe ser una lista no vacia")

        if len(columnas) != len(set(columnas)):
            raise ConfiguracionInvalida(f"Lista de columnas duplicadas en '{tabla_raw}': {columnas}")

        fuente = Fuente(
            tabla_raw=tabla_raw,
            tipo=tipo,
            origen=origen,
            columnas=tuple(str(c) for c in columnas),
        )
        fuentes.append(fuente)

    return fuentes
