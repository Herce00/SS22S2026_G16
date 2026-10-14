SELECT
    ROW_NUMBER() OVER (ORDER BY id_cliente)::INTEGER AS cliente_key,
    id_cliente,
    nit,
    nombre,
    tipo_cliente,
    municipio,
    departamento,
    fecha_alta
FROM {{ ref('stg_oltp__cliente') }}
