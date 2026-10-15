SELECT
    {{ convertir_seguro('id_venta', 'BIGINT') }} AS id_venta,
    {{ convertir_seguro('fecha', 'DATE') }} AS fecha,
    {{ convertir_seguro('id_cliente', 'INTEGER') }} AS id_cliente,
    {{ convertir_seguro('id_sucursal', 'INTEGER') }} AS id_sucursal,
    NULLIF(TRIM(canal), '') AS canal,
    NULLIF(TRIM(metodo_pago), '') AS metodo_pago,
    NULLIF(TRIM(estado), '') AS estado,
    _loaded_at
FROM {{ source('oltp', 'venta') }}
