"""Carga los casos de calidad opcionales sobre una copia de raw (schema raw_calidad).

No toca raw, staging ni marts. Crea raw_calidad como copia de las tablas de raw y aplica cada caso
de data/casos_calidad_opcionales.csv a una fila distinta de la tabla que le corresponde. Despues se
prueba con: dbt test --vars '{schema_raw: raw_calidad, prefijo_schema: cierre_}'

Uso (dentro del contenedor airflow-scheduler, por donde corre el DAG):
    python /opt/airflow/sql/calidad/cargar_casos_calidad.py            # crea raw_calidad y aplica los casos
    python /opt/airflow/sql/calidad/cargar_casos_calidad.py --limpiar  # elimina raw_calidad y los schemas de prueba

Salida: una linea por caso, APLICA (con la tabla y la fila modificada) o NO APLICA (con el motivo).
"""
import argparse
import csv
import sys

from psycopg import sql

from sgfood_ingesta.conexiones import conectar_dw
from sgfood_ingesta.config import listar_fuentes

CSV_POR_DEFECTO = "/opt/airflow/data/casos_calidad_opcionales.csv"
SCHEMA_CALIDAD = "raw_calidad"
SCHEMAS_DE_PRUEBA = ("raw_calidad", "cierre_staging", "cierre_marts")

# Nombres de entidad del catalogo que no coinciden con la tabla de raw
ENTIDAD_A_TABLA = {"inventario": "inventario_bodega"}


def leer_casos(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def limpiar(conn):
    with conn.cursor() as cur:
        for esquema in SCHEMAS_DE_PRUEBA:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema)))
    conn.commit()


def cargar(conn, casos):
    tablas_raw = [f.tabla_raw for f in listar_fuentes()]
    limpiar(conn)
    with conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(SCHEMA_CALIDAD)))
        for tabla in tablas_raw:
            cur.execute(
                sql.SQL("CREATE TABLE {}.{} AS SELECT * FROM raw.{}").format(
                    sql.Identifier(SCHEMA_CALIDAD), sql.Identifier(tabla), sql.Identifier(tabla)
                )
            )
        # cada caso modifica una fila distinta de su tabla, para que cada falla se pueda atribuir
        usadas = {}
        resultado = []
        for caso in casos:
            entidad, campo, valor = caso["entidad"], caso["campo"], caso["valor_prueba"]
            tabla = ENTIDAD_A_TABLA.get(entidad, entidad)
            if tabla not in tablas_raw:
                resultado.append(("NO APLICA", entidad, campo, f"la entidad {entidad} no corresponde a ninguna tabla de raw"))
                continue
            cur.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name = %s",
                (SCHEMA_CALIDAD, tabla, campo),
            )
            if cur.fetchone() is None:
                resultado.append(("NO APLICA", entidad, campo, f"la tabla {tabla} no tiene la columna {campo}"))
                continue
            fila = usadas.get(tabla, 0)
            usadas[tabla] = fila + 1
            cur.execute(
                sql.SQL(
                    "UPDATE {esq}.{tab} SET {col} = %s "
                    "WHERE ctid = (SELECT ctid FROM {esq}.{tab} ORDER BY ctid OFFSET %s LIMIT 1)"
                ).format(esq=sql.Identifier(SCHEMA_CALIDAD), tab=sql.Identifier(tabla), col=sql.Identifier(campo)),
                (valor, fila),
            )
            resultado.append(("APLICA", entidad, campo, f"{tabla}, fila {fila + 1}, valor '{valor}' ({caso['tipo_incidencia']})"))
    conn.commit()
    return resultado


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--csv", default=CSV_POR_DEFECTO)
    parser.add_argument("--limpiar", action="store_true", help="elimina raw_calidad y los schemas de prueba")
    args = parser.parse_args(argv)
    conn = conectar_dw()
    try:
        if args.limpiar:
            limpiar(conn)
            print("raw_calidad y schemas de prueba eliminados")
            return 0
        for estado, entidad, campo, detalle in cargar(conn, leer_casos(args.csv)):
            print(f"{estado}\t{entidad}.{campo}\t{detalle}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
