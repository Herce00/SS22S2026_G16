SELECT
    CASE
        WHEN TRIM(id_devolucion) ~ '^[0-9]+$'
        THEN TRIM(id_devolucion)::INTEGER
    END AS id_devolucion,
    CASE
        WHEN TRIM(fecha) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha)::DATE
    END AS fecha,
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
    NULLIF(TRIM(motivo), '') AS motivo,
    _loaded_at
FROM {{ source('archivos', 'devoluciones') }}
