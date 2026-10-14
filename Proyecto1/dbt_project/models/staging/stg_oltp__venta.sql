SELECT
    CASE
        WHEN TRIM(id_venta) ~ '^[0-9]+$'
        THEN TRIM(id_venta)::BIGINT
    END AS id_venta,
    CASE
        WHEN TRIM(fecha) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha)::DATE
    END AS fecha,
    CASE
        WHEN TRIM(id_cliente) ~ '^[0-9]+$'
        THEN TRIM(id_cliente)::INTEGER
    END AS id_cliente,
    CASE
        WHEN TRIM(id_sucursal) ~ '^[0-9]+$'
        THEN TRIM(id_sucursal)::INTEGER
    END AS id_sucursal,
    NULLIF(TRIM(canal), '') AS canal,
    NULLIF(TRIM(metodo_pago), '') AS metodo_pago,
    NULLIF(TRIM(estado), '') AS estado,
    _loaded_at
FROM {{ source('oltp', 'venta') }}
