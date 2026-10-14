SELECT
    MD5(CONCAT_WS('|', p.id_proveedor, p.id_producto, p.fecha_vigencia)) AS precio_proveedor_key,
    p.id_proveedor,
    p.proveedor,
    d.producto_key,
    TO_CHAR(p.fecha_vigencia, 'YYYYMMDD')::INTEGER AS fecha_key,
    p.costo_proveedor,
    p.plazo_dias
FROM {{ ref('int_precios_proveedor') }} AS p
LEFT JOIN {{ ref('dim_producto') }} AS d ON p.id_producto = d.id_producto
