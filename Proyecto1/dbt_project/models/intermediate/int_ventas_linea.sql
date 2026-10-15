SELECT
    vd.id_detalle,
    vd.id_venta,
    v.fecha,
    v.id_cliente,
    v.id_sucursal,
    vd.id_producto,
    v.canal,
    v.metodo_pago,
    v.estado,
    vd.cantidad,
    vd.precio_unitario,
    vd.descuento,
    vd.subtotal,
    vd.cantidad * vd.precio_unitario AS importe_bruto,
    vd.cantidad * vd.precio_unitario * vd.descuento AS importe_descuento,
    GREATEST(vd._loaded_at, v._loaded_at) AS _loaded_at
FROM {{ ref('stg_oltp__venta_detalle') }} AS vd
INNER JOIN {{ ref('stg_oltp__venta') }} AS v
    ON vd.id_venta = v.id_venta
