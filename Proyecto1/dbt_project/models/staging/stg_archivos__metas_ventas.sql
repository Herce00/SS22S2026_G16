SELECT
    CASE
        WHEN TRIM(periodo) ~ '^[0-9]{4}-[0-9]{2}$'
        THEN TRIM(periodo)
    END AS periodo,
    CASE
        WHEN TRIM(id_sucursal) ~ '^[0-9]+$'
        THEN TRIM(id_sucursal)::INTEGER
    END AS id_sucursal,
    CASE
        WHEN TRIM(meta_ventas) ~ '^[0-9]+(\.[0-9]+)?$'
        THEN TRIM(meta_ventas)::NUMERIC(14,2)
    END AS meta_ventas,
    CASE
        WHEN TRIM(meta_unidades) ~ '^[0-9]+$'
        THEN TRIM(meta_unidades)::INTEGER
    END AS meta_unidades,
    _loaded_at
FROM {{ source('archivos', 'metas_ventas') }}
