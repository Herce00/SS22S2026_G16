{#- Usa el schema personalizado tal cual (staging, marts), sin el prefijo del schema del perfil.
    La variable prefijo_schema permite escribir en schemas paralelos (por ejemplo cierre_staging)
    para probar contra una copia de raw sin tocar staging ni marts. Por defecto es vacia. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ var('prefijo_schema', '') }}{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
