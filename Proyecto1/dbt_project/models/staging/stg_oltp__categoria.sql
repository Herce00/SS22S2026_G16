SELECT
    CASE
        WHEN TRIM(id_categoria) ~ '^[0-9]+$'
        THEN TRIM(id_categoria)::INTEGER
    END AS id_categoria,
    NULLIF(TRIM(nombre), '') AS nombre,
    _loaded_at
FROM {{ source('oltp', 'categoria') }}
