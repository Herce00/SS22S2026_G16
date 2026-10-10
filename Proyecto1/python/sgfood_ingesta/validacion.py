"""Módulo de validación de calidad de datos, conteos y pruebas SQL."""
from dataclasses import dataclass
import logging
import os
from typing import Optional

from psycopg import sql

from sgfood_ingesta.carga import obtener_ruta_data_dir
from sgfood_ingesta.config import Fuente, listar_fuentes
from sgfood_ingesta.conexiones import conectar_dw, conectar_src
from sgfood_ingesta.errores import ValidacionFallida
from sgfood_ingesta.extraccion import extraer_filas_csv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConteoTabla:
    tabla_raw: str
    origen: str
    filas_fuente: int
    filas_raw: int


@dataclass(frozen=True)
class ResultadoValidacionSql:
    archivo: str
    filas_devueltas: int
    muestra: tuple[tuple, ...]


def contar_fuentes_y_raw() -> list[ConteoTabla]:
    """Cuenta las filas de cada fuente en su origen y en la tabla correspondiente de raw."""
    fuentes = listar_fuentes()
    resultados: list[ConteoTabla] = []

    conn_dw = conectar_dw()
    conn_src = None

    try:
        cur_dw = conn_dw.cursor()
        for f in fuentes:
            # 1. Contar filas en la fuente
            if f.tipo == "postgres":
                if conn_src is None:
                    conn_src = conectar_src()
                partes = f.origen.split(".", 1)
                schema, tabla = partes[0], partes[1]
                with conn_src.cursor() as cur_src:
                    query_src = sql.SQL("SELECT COUNT(*) FROM {schema}.{tabla}").format(
                        schema=sql.Identifier(schema),
                        tabla=sql.Identifier(tabla),
                    )
                    cur_src.execute(query_src)
                    filas_fuente = cur_src.fetchone()[0]
            elif f.tipo == "csv":
                data_dir = obtener_ruta_data_dir()
                ruta_csv = os.path.join(data_dir, f.origen)
                filas_fuente = sum(1 for _ in extraer_filas_csv(ruta_csv, f.columnas))
            else:
                raise ValueError(f"Tipo de fuente desconocido: '{f.tipo}'")

            # 2. Contar filas en raw.<tabla_raw> en el DW
            query_dw = sql.SQL("SELECT COUNT(*) FROM raw.{tabla}").format(
                tabla=sql.Identifier(f.tabla_raw)
            )
            cur_dw.execute(query_dw)
            filas_raw = cur_dw.fetchone()[0]

            conteo = ConteoTabla(
                tabla_raw=f.tabla_raw,
                origen=f.origen,
                filas_fuente=filas_fuente,
                filas_raw=filas_raw,
            )
            resultados.append(conteo)
    finally:
        conn_dw.close()
        if conn_src is not None:
            conn_src.close()

    return resultados


def validar_conteos(conteos: Optional[list[ConteoTabla]] = None) -> list[ConteoTabla]:
    """Registra el conteo por tabla y el total. Lanza ValidacionFallida si alguna no coincide."""
    if conteos is None:
        conteos = contar_fuentes_y_raw()

    total_fuente = sum(c.filas_fuente for c in conteos)
    total_raw = sum(c.filas_raw for c in conteos)

    logger.info(
        "Validando conteos: %d tablas verificadas, total fuente=%d, total raw=%d",
        len(conteos),
        total_fuente,
        total_raw,
    )

    for c in conteos:
        logger.info(
            "Tabla '%s' (origen: '%s'): fuente=%d, raw=%d",
            c.tabla_raw,
            c.origen,
            c.filas_fuente,
            c.filas_raw,
        )

    discrepancias = [c for c in conteos if c.filas_fuente != c.filas_raw]
    if discrepancias:
        detalles = [
            f"tabla '{d.tabla_raw}' ({d.filas_fuente} en fuente vs {d.filas_raw} en raw)"
            for d in discrepancias
        ]
        msg = f"Discrepancia de conteos en {len(discrepancias)} tabla(s): {', '.join(detalles)}"
        logger.error(msg)
        raise ValidacionFallida(msg)

    return conteos
