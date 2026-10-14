SELECT
    ROW_NUMBER() OVER (ORDER BY id_categoria)::INTEGER AS categoria_key,
    id_categoria,
    nombre
FROM {{ ref('stg_oltp__categoria') }}
