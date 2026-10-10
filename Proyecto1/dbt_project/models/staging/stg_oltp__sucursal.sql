-- Modelo de ejemplo. raw entrega todas las columnas como TEXT; aqui se convierten los tipos.
-- La conversion es tolerante: un valor que no es un entero queda en NULL en lugar de
-- romper el modelo, y la prueba not_null de _staging.yml lo reporta.
SELECT
    CASE WHEN id_sucursal ~ '^[0-9]+$' THEN id_sucursal::int END AS id_sucursal,
    nombre,
    ciudad,
    departamento,
    _loaded_at
FROM {{ source('oltp', 'sucursal') }}
