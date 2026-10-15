SELECT
    {{ convertir_seguro('id_categoria', 'INTEGER') }} AS id_categoria,
    NULLIF(TRIM(nombre), '') AS nombre,
    _loaded_at
FROM {{ source('oltp', 'categoria') }}
