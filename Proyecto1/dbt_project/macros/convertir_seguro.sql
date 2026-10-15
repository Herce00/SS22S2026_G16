{#- Convierte una columna TEXT a otro tipo y devuelve NULL si el valor no es valido.

    Usa pg_input_is_valid (PostgreSQL 16), que aplica el mismo analizador que el cast: detecta
    fechas imposibles (2026-02-30), meses 13 y desbordes de NUMERIC(5,4) o INTEGER sin
    reimplementar las reglas con expresiones regulares.

    Reglas de negocio que se conservan como condiciones explicitas:
      - DATE: solo formato ISO AAAA-MM-DD (el contrato raw no admite otros formatos).
      - Enteros y decimales: no negativos y que empiecen con un digito
        (excluye signos, NaN e Infinity). Pasar no_negativo=false para admitirlos.

    Uso: {{ convertir_seguro('id_venta', 'BIGINT') }}
-#}
{% macro convertir_seguro(columna, tipo, no_negativo=true) -%}
    CASE
        WHEN pg_input_is_valid(TRIM({{ columna }}), '{{ tipo }}')
        {%- if tipo | lower == 'date' %}
            AND TRIM({{ columna }}) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        {%- elif no_negativo %}
            AND TRIM({{ columna }}) ~ '^[0-9]'
        {%- endif %}
        THEN TRIM({{ columna }})::{{ tipo }}
    END
{%- endmacro %}
