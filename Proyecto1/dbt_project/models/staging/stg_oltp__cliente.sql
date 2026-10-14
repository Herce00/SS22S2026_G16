SELECT
    CASE
        WHEN TRIM(id_cliente) ~ '^[0-9]+$'
        THEN TRIM(id_cliente)::INTEGER
    END AS id_cliente,
    NULLIF(TRIM(nit), '') AS nit,
    NULLIF(TRIM(nombre), '') AS nombre,
    NULLIF(TRIM(tipo_cliente), '') AS tipo_cliente,
    NULLIF(TRIM(municipio), '') AS municipio,
    NULLIF(TRIM(departamento), '') AS departamento,
    CASE
        WHEN TRIM(fecha_alta) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN TRIM(fecha_alta)::DATE
    END AS fecha_alta,
    _loaded_at
FROM {{ source('oltp', 'cliente') }}
