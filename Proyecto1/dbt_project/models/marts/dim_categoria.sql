SELECT
    {{ clave_sustituta(['id_categoria']) }} AS categoria_key,
    id_categoria,
    nombre
FROM {{ ref('stg_oltp__categoria') }}
