"""Lectura y validación de fuentes.yml."""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Fuente:
    tabla_raw: str
    tipo: Literal["postgres", "csv"]
    origen: str
    columnas: tuple[str, ...]
