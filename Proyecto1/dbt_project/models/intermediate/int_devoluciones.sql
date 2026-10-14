SELECT
    d.id_devolucion,
    d.fecha,
    d.id_venta,
    d.id_producto,
    d.cantidad,
    d.motivo,
    d._loaded_at
FROM {{ ref('stg_archivos__devoluciones') }} AS d
