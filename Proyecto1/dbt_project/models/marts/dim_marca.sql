SELECT
    {{ clave_sustituta(['id_marca']) }} AS marca_key,
    id_marca,
    nombre
FROM {{ ref('stg_oltp__marca') }}
