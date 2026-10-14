WITH fuente AS (

    SELECT
        id_producto,
        sku,
        nombre,
        id_categoria,
        id_marca,
        unidad_medida,
        costo_base,
        precio_lista,
        activo
    FROM {{ source('oltp', 'producto') }}

),

tipado AS (

    SELECT
        CASE
            WHEN TRIM(id_producto) ~ '^[0-9]+$'
            THEN TRIM(id_producto)::INTEGER
        END AS id_producto,

        NULLIF(TRIM(sku), '') AS sku,
        NULLIF(TRIM(nombre), '') AS nombre,

        CASE
            WHEN TRIM(id_categoria) ~ '^[0-9]+$'
            THEN TRIM(id_categoria)::INTEGER
        END AS id_categoria,

        CASE
            WHEN TRIM(id_marca) ~ '^[0-9]+$'
            THEN TRIM(id_marca)::INTEGER
        END AS id_marca,

        NULLIF(TRIM(unidad_medida), '') AS unidad_medida,

        CASE
            WHEN TRIM(costo_base) ~ '^[0-9]+(\.[0-9]+)?$'
            THEN TRIM(costo_base)::NUMERIC(12,2)
        END AS costo_base,

        CASE
            WHEN TRIM(precio_lista) ~ '^[0-9]+(\.[0-9]+)?$'
            THEN TRIM(precio_lista)::NUMERIC(12,2)
        END AS precio_lista,

        CASE
            WHEN LOWER(TRIM(activo)) IN ('true', 'false')
            THEN LOWER(TRIM(activo))::BOOLEAN
        END AS activo

    FROM fuente

)

SELECT *
FROM tipado