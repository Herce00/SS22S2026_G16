"""Pruebas unitarias de construcción de consultas para fuentes PostgreSQL."""
import pytest
from psycopg import sql

from sgfood_ingesta.config import Fuente, listar_fuentes
from sgfood_ingesta.extraccion import construir_consulta_extraccion


def test_consulta_postgres_formato_y_orden():
    """La consulta convierte cada columna con ::text, respeta el orden y califica schema.tabla."""
    origen = "oltp_sgfood.venta"
    columnas = ("id_venta", "fecha", "total", "cliente_id")

    query = construir_consulta_extraccion(origen, columnas)
    assert isinstance(query, sql.Composed)

    rendered = query.as_string(None)
    esperado = (
        'SELECT "id_venta"::text, "fecha"::text, "total"::text, "cliente_id"::text '
        'FROM "oltp_sgfood"."venta"'
    )
    assert rendered == esperado
    assert "ORDER BY" not in rendered.upper()
    assert "SELECT *" not in rendered.upper()


def test_consulta_postgres_con_fuente():
    """Permite pasar directamente una instancia de Fuente de tipo postgres."""
    fuentes_postgres = [f for f in listar_fuentes() if f.tipo == "postgres"]
    assert len(fuentes_postgres) > 0

    for fuente in fuentes_postgres:
        query = construir_consulta_extraccion(fuente)
        rendered = query.as_string(None)
        schema, tabla = fuente.origen.split(".", 1)
        assert f'FROM "{schema}"."{tabla}"' in rendered
        for col in fuente.columnas:
            assert f'"{col}"::text' in rendered


def test_consulta_postgres_escape_caracteres_especiales():
    """Caracteres especiales como comillas y punto y coma se escapan como identificadores."""
    origen = 'schema"peligroso.tabla"inyectada; DROP TABLE users; --'
    columnas = ('col"con"comillas', 'col;maliciosa')

    query = construir_consulta_extraccion(origen, columnas)
    rendered = query.as_string(None)

    # Psycopg duplica las comillas dobles en identificadores: "col""con""comillas"
    assert '"col""con""comillas"::text' in rendered
    assert '"col;maliciosa"::text' in rendered
    assert '"schema""peligroso"."tabla""inyectada; DROP TABLE users; --"' in rendered
    # No debe haber texto de inyección fuera de los identificadores escapados
    assert rendered.startswith("SELECT ")
    assert " FROM " in rendered
