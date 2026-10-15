{{ config(
    post_hook=[
        "{{ clave_primaria('producto_key') }}",
        "{{ clave_foranea('categoria_key', 'dim_categoria', 'categoria_key') }}",
        "{{ clave_foranea('marca_key', 'dim_marca', 'marca_key') }}"
    ]
) }}

SELECT
    {{ clave_sustituta(['p.id_producto']) }} AS producto_key,
    p.id_producto,
    p.sku,
    p.nombre,
    c.categoria_key,
    m.marca_key,
    p.unidad_medida,
    p.costo_base,
    p.precio_lista,
    p.activo
FROM {{ ref('stg_oltp__producto') }} AS p
LEFT JOIN {{ ref('dim_categoria') }} AS c
    ON p.id_categoria = c.id_categoria
LEFT JOIN {{ ref('dim_marca') }} AS m
    ON p.id_marca = m.id_marca
