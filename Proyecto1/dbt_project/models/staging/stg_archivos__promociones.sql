SELECT
    CASE
        WHEN TRIM(id_promocion) ~ '^[0-9]+$'
        THEN TRIM(id_promocion)::INTEGER
    END AS id_promocion,
    NULLIF(TRIM(nombre), '') AS nombre,
    CASE
        WHEN TRIM(fecha_inicio) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha_inicio)::DATE
    END AS fecha_inicio,
    CASE
        WHEN TRIM(fecha_fin) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha_fin)::DATE
    END AS fecha_fin,
    CASE
        WHEN TRIM(id_categoria) ~ '^[0-9]+$'
        THEN TRIM(id_categoria)::INTEGER
    END AS id_categoria,
    CASE
        WHEN TRIM(porcentaje_descuento) ~ '^[0-9]+(\.[0-9]+)?$'
        THEN TRIM(porcentaje_descuento)::NUMERIC(5,4)
    END AS porcentaje_descuento,
    _loaded_at
FROM {{ source('archivos', 'promociones') }}
