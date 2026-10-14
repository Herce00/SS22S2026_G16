SELECT
    CASE
        WHEN TRIM(id_proveedor) ~ '^[0-9]+$'
        THEN TRIM(id_proveedor)::INTEGER
    END AS id_proveedor,
    NULLIF(TRIM(proveedor), '') AS proveedor,
    CASE
        WHEN TRIM(id_producto) ~ '^[0-9]+$'
        THEN TRIM(id_producto)::INTEGER
    END AS id_producto,
    CASE
        WHEN TRIM(costo_proveedor) ~ '^[0-9]+(\.[0-9]+)?$'
        THEN TRIM(costo_proveedor)::NUMERIC(12,2)
    END AS costo_proveedor,
    CASE
        WHEN TRIM(plazo_dias) ~ '^[0-9]+$'
        THEN TRIM(plazo_dias)::INTEGER
    END AS plazo_dias,
    CASE
        WHEN TRIM(fecha_vigencia) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha_vigencia)::DATE
    END AS fecha_vigencia,
    _loaded_at
FROM {{ source('archivos', 'proveedores_precios') }}
