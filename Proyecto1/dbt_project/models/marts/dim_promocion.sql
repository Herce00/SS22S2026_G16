{{ config(
    post_hook=[
        "{{ clave_primaria('promocion_key') }}",
        "{{ clave_foranea('fecha_inicio_key', 'dim_fecha', 'fecha_key') }}",
        "{{ clave_foranea('fecha_fin_key', 'dim_fecha', 'fecha_key') }}",
        "{{ clave_foranea('categoria_key', 'dim_categoria', 'categoria_key') }}"
    ]
) }}

SELECT
    {{ clave_sustituta(['p.id_promocion']) }} AS promocion_key,
    p.id_promocion,
    p.nombre,
    TO_CHAR(p.fecha_inicio, 'YYYYMMDD')::INTEGER AS fecha_inicio_key,
    TO_CHAR(p.fecha_fin, 'YYYYMMDD')::INTEGER AS fecha_fin_key,
    c.categoria_key,
    p.porcentaje_descuento
FROM {{ ref('stg_archivos__promociones') }} AS p
LEFT JOIN {{ ref('dim_categoria') }} AS c
    ON p.id_categoria = c.id_categoria
