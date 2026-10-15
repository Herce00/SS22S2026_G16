{#- Clave sustituta determinista: MD5 de la clave natural.

    La misma entidad recibe la misma clave en cualquier ejecucion, sin depender del orden ni de
    cuantas filas existan. Acepta una o varias columnas (se concatenan con '|').

    Uso: {{ clave_sustituta(['id_cliente']) }} AS cliente_key
-#}
{% macro clave_sustituta(columnas) -%}
    MD5({% for c in columnas %}{{ c }}::TEXT{% if not loop.last %} || '|' || {% endif %}{% endfor %})
{%- endmacro %}
