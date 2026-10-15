{{ config(
    post_hook=[
        "{{ clave_primaria('inventario_snapshot_key') }}",
        "{{ clave_foranea('fecha_key', 'dim_fecha', 'fecha_key') }}",
        "{{ clave_foranea('sucursal_key', 'dim_sucursal', 'sucursal_key') }}",
        "{{ clave_foranea('producto_key', 'dim_producto', 'producto_key') }}"
    ]
) }}

SELECT
    MD5(CONCAT_WS('|', i.fecha_corte, i.id_sucursal, i.id_producto, i.lote)) AS inventario_snapshot_key,
    TO_CHAR(i.fecha_corte, 'YYYYMMDD')::INTEGER AS fecha_key,
    s.sucursal_key,
    p.producto_key,
    i.lote,
    i.fecha_vencimiento,
    i.stock_disponible,
    i.stock_minimo,
    i.stock_maximo,
    i.stock_faltante,
    i.stock_sobrante,
    i.esta_bajo_minimo,
    i.esta_sobre_maximo
FROM {{ ref('int_inventario_snapshot') }} AS i
LEFT JOIN {{ ref('dim_sucursal') }} AS s ON i.id_sucursal = s.id_sucursal
LEFT JOIN {{ ref('dim_producto') }} AS p ON i.id_producto = p.id_producto
