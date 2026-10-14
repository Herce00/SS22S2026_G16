SELECT
    CASE
        WHEN TRIM(id_detalle) ~ '^[0-9]+$'
        THEN TRIM(id_detalle)::BIGINT
    END AS id_detalle,
    CASE
        WHEN TRIM(id_venta) ~ '^[0-9]+$'
        THEN TRIM(id_venta)::BIGINT
    END AS id_venta,
    CASE
        WHEN TRIM(id_producto) ~ '^[0-9]+$'
        THEN TRIM(id_producto)::INTEGER
    END AS id_producto,
    CASE
        WHEN TRIM(cantidad) ~ '^[0-9]+$'
        THEN TRIM(cantidad)::INTEGER
    END AS cantidad,
    CASE
        WHEN TRIM(precio_unitario) ~ '^[0-9]+(\.[0-9]+)?$'
        THEN TRIM(precio_unitario)::NUMERIC(12,2)
    END AS precio_unitario,
    CASE
        WHEN TRIM(descuento) ~ '^[0-9]+(\.[0-9]+)?$'
        THEN TRIM(descuento)::NUMERIC(5,4)
    END AS descuento,
    CASE
        WHEN TRIM(subtotal) ~ '^[0-9]+(\.[0-9]+)?$'
        THEN TRIM(subtotal)::NUMERIC(14,2)
    END AS subtotal,
    _loaded_at
FROM {{ source('oltp', 'venta_detalle') }}
