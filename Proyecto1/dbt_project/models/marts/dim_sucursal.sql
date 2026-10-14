SELECT
    ROW_NUMBER() OVER (ORDER BY id_sucursal)::INTEGER AS sucursal_key,
    id_sucursal,
    nombre,
    ciudad,
    departamento
FROM {{ ref('stg_oltp__sucursal') }}
