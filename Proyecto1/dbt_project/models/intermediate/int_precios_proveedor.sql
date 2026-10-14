SELECT
    p.id_proveedor,
    p.proveedor,
    p.id_producto,
    p.costo_proveedor,
    p.plazo_dias,
    p.fecha_vigencia,
    p._loaded_at
FROM {{ ref('stg_archivos__proveedores_precios') }} AS p
