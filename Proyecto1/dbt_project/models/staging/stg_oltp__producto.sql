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
        {{ convertir_seguro('id_producto', 'INTEGER') }} AS id_producto,

        NULLIF(TRIM(sku), '') AS sku,
        NULLIF(TRIM(nombre), '') AS nombre,

        {{ convertir_seguro('id_categoria', 'INTEGER') }} AS id_categoria,

        {{ convertir_seguro('id_marca', 'INTEGER') }} AS id_marca,

        NULLIF(TRIM(unidad_medida), '') AS unidad_medida,

        {{ convertir_seguro('costo_base', 'NUMERIC(12,2)') }} AS costo_base,

        {{ convertir_seguro('precio_lista', 'NUMERIC(12,2)') }} AS precio_lista,

        CASE
            WHEN LOWER(TRIM(activo)) IN ('true', 'false')
            THEN LOWER(TRIM(activo))::BOOLEAN
        END AS activo

    FROM fuente

)

SELECT *
FROM tipado