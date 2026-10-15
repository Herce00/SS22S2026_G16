{{ config(
    post_hook=[
        "{{ clave_primaria('precio_proveedor_key') }}",
        "{{ clave_foranea('fecha_key', 'dim_fecha', 'fecha_key') }}",
        "{{ clave_foranea('producto_key', 'dim_producto', 'producto_key') }}"
    ]
) }}

SELECT
    MD5(CONCAT_WS('|', p.id_proveedor, p.id_producto, p.fecha_vigencia)) AS precio_proveedor_key,
    p.id_proveedor,
    p.proveedor,
    d.producto_key,
    TO_CHAR(p.fecha_vigencia, 'YYYYMMDD')::INTEGER AS fecha_key,
    p.costo_proveedor,
    p.plazo_dias
FROM {{ ref('int_precios_proveedor') }} AS p
LEFT JOIN {{ ref('dim_producto') }} AS d ON p.id_producto = d.id_producto
