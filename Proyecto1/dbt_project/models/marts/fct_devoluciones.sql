{{ config(
    post_hook=[
        "{{ clave_primaria('devolucion_key') }}",
        "{{ clave_foranea('fecha_key', 'dim_fecha', 'fecha_key') }}",
        "{{ clave_foranea('producto_key', 'dim_producto', 'producto_key') }}"
    ]
) }}

SELECT
    d.id_devolucion AS devolucion_key,
    d.id_devolucion,
    TO_CHAR(d.fecha, 'YYYYMMDD')::INTEGER AS fecha_key,
    d.id_venta,
    p.producto_key,
    d.cantidad,
    d.motivo
FROM {{ ref('int_devoluciones') }} AS d
LEFT JOIN {{ ref('dim_producto') }} AS p ON d.id_producto = p.id_producto
