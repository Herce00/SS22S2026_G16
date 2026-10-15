SELECT
    {{ convertir_seguro('fecha_corte', 'DATE') }} AS fecha_corte,
    {{ convertir_seguro('id_sucursal', 'INTEGER') }} AS id_sucursal,
    {{ convertir_seguro('id_producto', 'INTEGER') }} AS id_producto,
    {{ convertir_seguro('stock_disponible', 'INTEGER') }} AS stock_disponible,
    {{ convertir_seguro('stock_minimo', 'INTEGER') }} AS stock_minimo,
    {{ convertir_seguro('stock_maximo', 'INTEGER') }} AS stock_maximo,
    NULLIF(TRIM(lote), '') AS lote,
    {{ convertir_seguro('fecha_vencimiento', 'DATE') }} AS fecha_vencimiento,
    _loaded_at
FROM {{ source('archivos', 'inventario_bodega') }}
