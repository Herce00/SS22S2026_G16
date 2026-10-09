"""Paquete de ingesta técnica para SG-Food."""
from datetime import datetime
from sgfood_ingesta.config import Fuente, cargar_configuracion
from sgfood_ingesta.ingesta import ResultadoCarga
from sgfood_ingesta.errores import (
    ErrorIngesta,
    ConfiguracionInvalida,
    FuenteDesconocida,
    EncabezadoInvalido,
    FilaInvalida,
    ConteoInconsistente,
)


def listar_fuentes() -> list[Fuente]:
    return cargar_configuracion()


def cargar_fuente(tabla_raw: str, loaded_at: datetime | None = None) -> ResultadoCarga:
    raise NotImplementedError


def cargar_todas(loaded_at: datetime | None = None) -> list[ResultadoCarga]:
    raise NotImplementedError


__all__ = [
    "Fuente",
    "ResultadoCarga",
    "listar_fuentes",
    "cargar_fuente",
    "cargar_todas",
    "ErrorIngesta",
    "ConfiguracionInvalida",
    "FuenteDesconocida",
    "EncabezadoInvalido",
    "FilaInvalida",
    "ConteoInconsistente",
]
