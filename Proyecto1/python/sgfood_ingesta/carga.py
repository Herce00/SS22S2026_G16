"""Carga transaccional de datos en el schema raw del Data Warehouse."""
import os
import time
from datetime import datetime
from typing import Iterator

from psycopg import sql

from sgfood_ingesta.config import Fuente
from sgfood_ingesta.conexiones import conectar_dw, conectar_src
from sgfood_ingesta.errores import ConteoInconsistente
from sgfood_ingesta.extraccion import extraer_filas_csv, extraer_filas_postgres


DEFAULT_DATA_DIR = "/opt/airflow/data"


def obtener_ruta_data_dir() -> str:
    """Resuelve el directorio de datos para archivos CSV."""
    env_dir = os.environ.get("SGFOOD_DATA_DIR")
    if env_dir:
        return env_dir
    if os.path.isdir(DEFAULT_DATA_DIR):
        return DEFAULT_DATA_DIR
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback_dir = os.path.join(base_dir, "data")
    return fallback_dir


def cargar_fuente_en_dw(
    fuente: Fuente,
    loaded_at: datetime,
) -> tuple[int, int, float]:
    """Carga una fuente en su tabla raw correspondiente en el DW.

    - Abre transacción con autocommit=False.
    - TRUNCATE raw.<tabla>.
    - COPY raw.<tabla> (columnas..., _loaded_at, _source) FROM STDIN.
    - Convierte valores None en NULL de Postgres mediante copy.write_row().
    - Verifica SELECT count(*) == filas_leidas antes de confirmar.
    - Ante cualquier error, la transacción se revierte preservando el estado previo.

    Retorna: (filas_leidas, filas_cargadas, duracion_segundos)
    """
    inicio = time.perf_counter()

    # Preparar el iterador de filas según el tipo de fuente
    conn_src = None
    try:
        if fuente.tipo == "postgres":
            conn_src = conectar_src()
            filas_iter: Iterator[tuple[str | None, ...]] = extraer_filas_postgres(conn_src, fuente)
        elif fuente.tipo == "csv":
            data_dir = obtener_ruta_data_dir()
            ruta_csv = os.path.join(data_dir, fuente.origen)
            filas_iter = extraer_filas_csv(ruta_csv, fuente.columnas)
        else:
            raise ValueError(f"Tipo de fuente desconocido: '{fuente.tipo}'")

        # Conectar al DW y ejecutar la carga dentro de una transacción
        with conectar_dw() as conn_dw:
            with conn_dw.transaction():
                with conn_dw.cursor() as cur:
                    # TRUNCATE tabla destino
                    truncate_sql = sql.SQL("TRUNCATE TABLE raw.{}").format(sql.Identifier(fuente.tabla_raw))
                    cur.execute(truncate_sql)

                    # Preparar sentencia COPY con columnas de negocio + auditoría
                    columnas_copy = [sql.Identifier(c) for c in fuente.columnas] + [
                        sql.Identifier("_loaded_at"),
                        sql.Identifier("_source"),
                    ]
                    copy_sql = sql.SQL("COPY raw.{} ({}) FROM STDIN").format(
                        sql.Identifier(fuente.tabla_raw),
                        sql.SQL(", ").join(columnas_copy),
                    )

                    filas_leidas = 0
                    with cur.copy(copy_sql) as copy:
                        for fila in filas_iter:
                            filas_leidas += 1
                            fila_con_auditoria = (*fila, loaded_at.isoformat(), fuente.origen)
                            copy.write_row(fila_con_auditoria)

                    # Verificar conteo de filas
                    count_sql = sql.SQL("SELECT count(*) FROM raw.{}").format(sql.Identifier(fuente.tabla_raw))
                    cur.execute(count_sql)
                    filas_cargadas = cur.fetchone()[0]

                    if filas_cargadas != filas_leidas:
                        raise ConteoInconsistente(
                            f"Discrepancia en tabla '{fuente.tabla_raw}': "
                            f"{filas_leidas} filas leídas vs {filas_cargadas} filas cargadas en raw"
                        )

        duracion = time.perf_counter() - inicio
        return filas_leidas, filas_cargadas, duracion

    finally:
        if conn_src is not None:
            conn_src.close()
