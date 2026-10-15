"""Utilidades compartidas por las pruebas de integracion de ajustes-cierre.

Todas ejecutan psql con ON_ERROR_STOP=1 y dbt dentro del contenedor airflow-scheduler.
"""
import json
import os
import subprocess

import pytest

from sgfood_ingesta.config import listar_fuentes

DBT_BIN = "/opt/dbt-venv/bin/dbt"
DBT_DIR = "/opt/airflow/dbt_project"
TOTAL_RAW_CONTRATO = 8864


def _proyecto1():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _leer_env():
    config = {}
    with open(os.path.join(_proyecto1(), ".env"), "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                config[k.strip()] = v.strip()
    return config


def _compose(*args, entrada=None):
    return subprocess.run(
        ["docker", "compose", *args],
        capture_output=True, text=True, cwd=_proyecto1(), input=entrada,
        encoding="utf-8",
    )


def psql(sql, servicio="dw"):
    """Ejecuta SQL en dw (por defecto) o src y devuelve las filas como lista de listas de texto."""
    env = _leer_env()
    prefijo = "DW" if servicio == "dw" else "SRC"
    res = _compose(
        "exec", "-T", servicio, "psql", "-v", "ON_ERROR_STOP=1",
        "-U", env[f"{prefijo}_USER"], "-d", env[f"{prefijo}_DB"],
        "-tA", "-F", "\t", "-f", "-", entrada=sql,
    )
    assert res.returncode == 0, f"psql fallo en {servicio}:\n{res.stderr}\n{sql[:300]}"
    return [fila.split("\t") for fila in res.stdout.splitlines() if fila != ""]


def escalar(sql, servicio="dw"):
    filas = psql(sql, servicio)
    assert filas, f"sin filas para: {sql}"
    return filas[-1][0]


def dbt(comando, variables=None, extra=()):
    """Ejecuta dbt en el scheduler; devuelve el CompletedProcess."""
    args = [
        "exec", "-T", "airflow-scheduler", DBT_BIN, *comando.split(),
        "--project-dir", DBT_DIR, "--profiles-dir", DBT_DIR, *extra,
    ]
    if variables:
        args += ["--vars", json.dumps(variables)]
    return _compose(*args)


def total_raw():
    """Suma de filas de las 12 tablas de raw (contrato: 8864)."""
    tablas = [f.tabla_raw for f in listar_fuentes()]
    union = " UNION ALL ".join(f"SELECT count(*) AS n FROM raw.{t}" for t in tablas)
    return int(escalar(f"SELECT sum(n) FROM ({union}) x"))


def conteos_marts():
    filas = psql(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='marts' ORDER BY 1"
    )
    resultado = {}
    for (t,) in filas:
        resultado[t] = int(escalar(f"SELECT count(*) FROM marts.{t}"))
    return resultado


@pytest.fixture
def raw_intacto():
    """Comprueba que raw conserva el total del contrato antes y despues de la prueba."""
    assert total_raw() == TOTAL_RAW_CONTRATO
    yield
    assert total_raw() == TOTAL_RAW_CONTRATO


@pytest.fixture
def copia_raw(raw_intacto):
    """Crea una copia de raw (schema raw_cierre) y limpia sus objetos al terminar.

    Los modelos de la corrida de prueba se escriben en cierre_staging y cierre_marts
    mediante la variable prefijo_schema, sin tocar staging ni marts.
    """
    tablas = [f.tabla_raw for f in listar_fuentes()]
    limpiar = (
        "DROP SCHEMA IF EXISTS raw_cierre CASCADE; "
        "DROP SCHEMA IF EXISTS cierre_staging CASCADE; "
        "DROP SCHEMA IF EXISTS cierre_marts CASCADE;"
    )
    psql(limpiar)
    creacion = "CREATE SCHEMA raw_cierre;" + "".join(
        f"CREATE TABLE raw_cierre.{t} AS SELECT * FROM raw.{t};" for t in tablas
    )
    psql(creacion)
    variables = {"schema_raw": "raw_cierre", "prefijo_schema": "cierre_"}
    try:
        yield variables
    finally:
        psql(limpiar)


def resumen(res, maximo=12):
    """Lineas relevantes (errores, fallas, resumen) de una salida de dbt, para mensajes de aserto."""
    claves = ("ERROR", "FAIL", "Error", "Done.", "out of range", "invalid input")
    lineas = [l.strip() for l in (res.stdout + res.stderr).splitlines() if any(k in l for k in claves)]
    return "\n".join(lineas[:maximo])
