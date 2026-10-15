SELECT
    {{ convertir_seguro('id_cliente', 'INTEGER') }} AS id_cliente,
    NULLIF(TRIM(nit), '') AS nit,
    NULLIF(TRIM(nombre), '') AS nombre,
    NULLIF(TRIM(tipo_cliente), '') AS tipo_cliente,
    NULLIF(TRIM(municipio), '') AS municipio,
    NULLIF(TRIM(departamento), '') AS departamento,
    {{ convertir_seguro('fecha_alta', 'DATE') }} AS fecha_alta,
    _loaded_at
FROM {{ source('oltp', 'cliente') }}
