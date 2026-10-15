SELECT
    {{ convertir_seguro('id_marca', 'INTEGER') }} AS id_marca,
    NULLIF(TRIM(nombre), '') AS nombre,
    _loaded_at
FROM {{ source('oltp', 'marca') }}
