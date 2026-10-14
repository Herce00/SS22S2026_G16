SELECT
    ROW_NUMBER() OVER (ORDER BY id_marca)::INTEGER AS marca_key,
    id_marca,
    nombre
FROM {{ ref('stg_oltp__marca') }}
