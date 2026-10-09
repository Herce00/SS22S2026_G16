"""Extracción de filas de texto desde postgres o csv."""
import csv
import os
from typing import Iterator

from psycopg import sql

from sgfood_ingesta.config import Fuente
from sgfood_ingesta.errores import (
    ConfiguracionInvalida,
    EncabezadoInvalido,
    FilaInvalida,
)


def construir_consulta_extraccion(
    fuente_o_origen: Fuente | str,
    columnas: tuple[str, ...] | None = None,
) -> sql.Composed:
    """Construye la consulta SELECT para extraer datos desde PostgreSQL.

    - Convierte cada columna con ::text usando sql.Identifier.
    - Respeta el orden declarado de las columnas.
    - Califica la tabla con su schema usando sql.Identifier.
    - Escapa identificadores especiales para prevenir inyección SQL.
    - No incluye ORDER BY ni SELECT *.
    """
    if isinstance(fuente_o_origen, Fuente):
        origen = fuente_o_origen.origen
        cols = fuente_o_origen.columnas
    else:
        origen = fuente_o_origen
        if columnas is None:
            raise ValueError("Se requieren columnas si se pasa origen como string")
        cols = columnas

    partes = origen.split(".", 1)
    if len(partes) != 2:
        raise ValueError(f"El origen postgres debe tener formato 'schema.tabla', recibido: '{origen}'")
    schema, tabla = partes[0], partes[1]

    col_items = [
        sql.SQL("{col}::text").format(col=sql.Identifier(c))
        for c in cols
    ]
    query = sql.SQL("SELECT {cols} FROM {schema}.{tabla}").format(
        cols=sql.SQL(", ").join(col_items),
        schema=sql.Identifier(schema),
        tabla=sql.Identifier(tabla),
    )
    return query


def extraer_filas_postgres(
    conn,
    fuente: Fuente,
) -> Iterator[tuple[str | None, ...]]:
    """Ejecuta la consulta construida y produce tuplas de texto desde PostgreSQL."""
    query = construir_consulta_extraccion(fuente)
    with conn.cursor() as cur:
        cur.execute(query)
        for row in cur:
            yield tuple(row)


def extraer_filas_csv(
    ruta_csv: str,
    columnas_esperadas: tuple[str, ...],
) -> Iterator[tuple[str | None, ...]]:
    """Lee un archivo CSV con utf-8-sig y produce tuplas de texto respetando el contrato.

    - La primera fila se compara contra columnas_esperadas.
    - Las lineas completamente vacias se ignoran.
    - Las filas con cantidad incorrecta de campos lanzan FilaInvalida con el numero de linea.
    - Las cadenas vacias se convierten en None (unica transformacion de valores).
    """
    if not os.path.isfile(ruta_csv):
        raise ConfiguracionInvalida(f"El archivo CSV no existe: '{ruta_csv}'")

    with open(ruta_csv, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        try:
            encabezado = next(reader)
        except StopIteration:
            raise EncabezadoInvalido(f"El archivo CSV '{ruta_csv}' esta vacio")

        if tuple(encabezado) != columnas_esperadas:
            raise EncabezadoInvalido(
                f"Encabezado de '{ruta_csv}' no coincide con el contrato.\n"
                f"Esperado: {columnas_esperadas}\n"
                f"Obtenido: {tuple(encabezado)}"
            )

        num_columnas = len(columnas_esperadas)

        for row in reader:
            # Omitir lineas completamente vacias
            if not row or (len(row) == 1 and row[0] == ""):
                continue

            linea_actual = reader.line_num
            if len(row) != num_columnas:
                raise FilaInvalida(
                    f"Fila en linea {linea_actual} de '{ruta_csv}' tiene {len(row)} campos, esperados {num_columnas}",
                    linea=linea_actual,
                )

            # Convertir "" en None, preservar espacios
            fila_transformada = tuple(None if val == "" else val for val in row)
            yield fila_transformada
