"""Paquete de ingesta técnica para SG-Food."""
from sgfood_ingesta.config import Fuente, listar_fuentes
from sgfood_ingesta.ingesta import ResultadoCarga, cargar_fuente, cargar_todas
from sgfood_ingesta.errores import (
    ErrorIngesta,
    ConfiguracionInvalida,
    FuenteDesconocida,
    EncabezadoInvalido,
    FilaInvalida,
    ConteoInconsistente,
    ValidacionFallida,
)
from sgfood_ingesta.validacion import (
    ConteoTabla,
    ResultadoValidacionSql,
    contar_fuentes_y_raw,
    validar_conteos,
)

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
    "ValidacionFallida",
    "ConteoTabla",
    "ResultadoValidacionSql",
    "contar_fuentes_y_raw",
    "validar_conteos",
]

