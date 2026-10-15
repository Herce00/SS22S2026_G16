{#- Clave sustituta determinista: MD5 de la clave natural.

    La misma entidad recibe la misma clave en cualquier ejecucion, sin depender del orden ni de
    cuantas filas existan. Acepta una o varias columnas (se concatenan con '|').

    Una columna nula se trata como texto vacio para que la clave nunca sea NULL: asi una clave
    natural invalida no impide crear la clave primaria fisica y dbt run termina; la prueba not_null
    de la clave natural es la que reporta el problema.

    Uso: {{ clave_sustituta(['id_cliente']) }} AS cliente_key
-#}
{% macro clave_sustituta(columnas) -%}
    MD5({% for c in columnas %}COALESCE({{ c }}::TEXT, ''){% if not loop.last %} || '|' || {% endif %}{% endfor %})
{%- endmacro %}
