SELECT
    CASE
        WHEN TRIM(fecha_corte) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha_corte)::DATE
    END AS fecha_corte,
    CASE
        WHEN TRIM(id_sucursal) ~ '^[0-9]+$'
        THEN TRIM(id_sucursal)::INTEGER
    END AS id_sucursal,
    CASE
        WHEN TRIM(id_producto) ~ '^[0-9]+$'
        THEN TRIM(id_producto)::INTEGER
    END AS id_producto,
    CASE
        WHEN TRIM(stock_disponible) ~ '^[0-9]+$'
        THEN TRIM(stock_disponible)::INTEGER
    END AS stock_disponible,
    CASE
        WHEN TRIM(stock_minimo) ~ '^[0-9]+$'
        THEN TRIM(stock_minimo)::INTEGER
    END AS stock_minimo,
    CASE
        WHEN TRIM(stock_maximo) ~ '^[0-9]+$'
        THEN TRIM(stock_maximo)::INTEGER
    END AS stock_maximo,
    NULLIF(TRIM(lote), '') AS lote,
    CASE
        WHEN TRIM(fecha_vencimiento) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha_vencimiento)::DATE
    END AS fecha_vencimiento,
    _loaded_at
FROM {{ source('archivos', 'inventario_bodega') }}
