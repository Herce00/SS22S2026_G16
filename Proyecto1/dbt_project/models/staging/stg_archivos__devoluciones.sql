SELECT
    {{ convertir_seguro('id_devolucion', 'INTEGER') }} AS id_devolucion,
    {{ convertir_seguro('fecha', 'DATE') }} AS fecha,
    {{ convertir_seguro('id_venta', 'BIGINT') }} AS id_venta,
    {{ convertir_seguro('id_producto', 'INTEGER') }} AS id_producto,
    {{ convertir_seguro('cantidad', 'INTEGER') }} AS cantidad,
    NULLIF(TRIM(motivo), '') AS motivo,
    _loaded_at
FROM {{ source('archivos', 'devoluciones') }}
