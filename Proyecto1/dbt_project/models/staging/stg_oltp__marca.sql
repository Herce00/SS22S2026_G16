SELECT
    CASE
        WHEN TRIM(id_marca) ~ '^[0-9]+$'
        THEN TRIM(id_marca)::INTEGER
    END AS id_marca,
    NULLIF(TRIM(nombre), '') AS nombre,
    _loaded_at
FROM {{ source('oltp', 'marca') }}
