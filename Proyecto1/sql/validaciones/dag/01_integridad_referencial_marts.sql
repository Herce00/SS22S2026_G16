SELECT 'ventas_fecha' AS validacion, v.venta_linea_key
FROM marts.fct_ventas_linea AS v
LEFT JOIN marts.dim_fecha AS d ON v.fecha_key = d.fecha_key
WHERE d.fecha_key IS NULL
UNION ALL
SELECT 'ventas_cliente', v.venta_linea_key
FROM marts.fct_ventas_linea AS v
LEFT JOIN marts.dim_cliente AS d ON v.cliente_key = d.cliente_key
WHERE d.cliente_key IS NULL
UNION ALL
SELECT 'ventas_sucursal', v.venta_linea_key
FROM marts.fct_ventas_linea AS v
LEFT JOIN marts.dim_sucursal AS d ON v.sucursal_key = d.sucursal_key
WHERE d.sucursal_key IS NULL
UNION ALL
SELECT 'ventas_producto', v.venta_linea_key
FROM marts.fct_ventas_linea AS v
LEFT JOIN marts.dim_producto AS d ON v.producto_key = d.producto_key
WHERE d.producto_key IS NULL
UNION ALL
SELECT 'inventario_producto', i.inventario_snapshot_key
FROM marts.fct_inventario_snapshot AS i
LEFT JOIN marts.dim_producto AS d ON i.producto_key = d.producto_key
WHERE d.producto_key IS NULL
UNION ALL
SELECT 'inventario_sucursal', i.inventario_snapshot_key
FROM marts.fct_inventario_snapshot AS i
LEFT JOIN marts.dim_sucursal AS d ON i.sucursal_key = d.sucursal_key
WHERE d.sucursal_key IS NULL;
