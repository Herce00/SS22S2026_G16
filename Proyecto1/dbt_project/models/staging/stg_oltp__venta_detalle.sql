SELECT
    {{ convertir_seguro('id_detalle', 'BIGINT') }} AS id_detalle,
    {{ convertir_seguro('id_venta', 'BIGINT') }} AS id_venta,
    {{ convertir_seguro('id_producto', 'INTEGER') }} AS id_producto,
    {{ convertir_seguro('cantidad', 'INTEGER') }} AS cantidad,
    {{ convertir_seguro('precio_unitario', 'NUMERIC(12,2)') }} AS precio_unitario,
    {{ convertir_seguro('descuento', 'NUMERIC(5,4)') }} AS descuento,
    {{ convertir_seguro('subtotal', 'NUMERIC(14,2)') }} AS subtotal,
    _loaded_at
FROM {{ source('oltp', 'venta_detalle') }}
