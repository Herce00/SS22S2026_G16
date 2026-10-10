"""Orquestación del flujo de ingesta técnica hacia raw."""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Optional

from sgfood_ingesta.carga import cargar_fuente_en_dw
from sgfood_ingesta.config import Fuente, listar_fuentes
from sgfood_ingesta.errores import FuenteDesconocida


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoCarga:
    tabla_raw: str
    origen: str
    filas_leidas: int
    filas_cargadas: int
    duracion_segundos: float
    loaded_at: datetime


def cargar_fuente(tabla_raw: str, loaded_at: Optional[datetime] = None) -> ResultadoCarga:
    """Carga una sola tabla de raw. Si loaded_at es None, usa UTC actual."""
    fuentes = listar_fuentes()
    fuente_seleccionada: Optional[Fuente] = None
    for f in fuentes:
        if f.tabla_raw == tabla_raw:
            fuente_seleccionada = f
            break

    if fuente_seleccionada is None:
        tablas_validas = ", ".join(f.tabla_raw for f in fuentes)
        raise FuenteDesconocida(
            f"Tabla '{tabla_raw}' no encontrada en la configuracion. "
            f"Tablas validas: [{tablas_validas}]"
        )

    ts = loaded_at if loaded_at is not None else datetime.now(timezone.utc)

    logger.info("Iniciando carga de '%s' desde '%s'...", fuente_seleccionada.tabla_raw, fuente_seleccionada.origen)
    filas_leidas, filas_cargadas, duracion = cargar_fuente_en_dw(fuente_seleccionada, ts)
    logger.info(
        "Carga finalizada para '%s': %d leidas, %d cargadas en %.2fs",
        fuente_seleccionada.tabla_raw,
        filas_leidas,
        filas_cargadas,
        duracion,
    )

    return ResultadoCarga(
        tabla_raw=fuente_seleccionada.tabla_raw,
        origen=fuente_seleccionada.origen,
        filas_leidas=filas_leidas,
        filas_cargadas=filas_cargadas,
        duracion_segundos=duracion,
        loaded_at=ts,
    )


def cargar_todas(loaded_at: Optional[datetime] = None) -> list[ResultadoCarga]:
    """Carga las 12 tablas en orden compartiendo el mismo loaded_at.

    Se detiene en el primer fallo; las tablas ya confirmadas quedan cargadas.
    """
    ts = loaded_at if loaded_at is not None else datetime.now(timezone.utc)
    fuentes = listar_fuentes()
    resultados: list[ResultadoCarga] = []

    logger.info("Iniciando carga completa de %d fuentes con loaded_at=%s...", len(fuentes), ts.isoformat())

    for fuente in fuentes:
        logger.info("Cargando '%s' desde '%s'...", fuente.tabla_raw, fuente.origen)
        filas_leidas, filas_cargadas, duracion = cargar_fuente_en_dw(fuente, ts)
        logger.info(
            "Completada '%s': %d leidas, %d cargadas en %.2fs",
            fuente.tabla_raw,
            filas_leidas,
            filas_cargadas,
            duracion,
        )
        res = ResultadoCarga(
            tabla_raw=fuente.tabla_raw,
            origen=fuente.origen,
            filas_leidas=filas_leidas,
            filas_cargadas=filas_cargadas,
            duracion_segundos=duracion,
            loaded_at=ts,
        )
        resultados.append(res)

    total_filas = sum(r.filas_cargadas for r in resultados)
    logger.info("Carga completa finalizada: %d tablas procesadas, %d filas cargadas.", len(resultados), total_filas)
    return resultados
