"""Orquestación interna de extracción y carga por tabla."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResultadoCarga:
    tabla_raw: str
    origen: str
    filas_leidas: int
    filas_cargadas: int
    duracion_segundos: float
    loaded_at: datetime
