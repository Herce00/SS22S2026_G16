SELECT
    id_sucursal::int as id_sucursal,
    nombre,
    ciudad,
    departamento,
    _loaded_at
FROM {{ source('oltp', 'sucursal') }}
