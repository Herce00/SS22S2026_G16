-- Pregunta: algun hecho apunta a una dimension que no existe, o tiene la clave vacia?
-- Resultado esperado: cero filas. Cubre los cinco hechos y todas sus claves foraneas.
-- Una clave nula tambien se reporta, porque el LEFT JOIN no encuentra la dimension.
SELECT 'ventas_fecha' AS validacion, v.venta_linea_key AS clave
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
SELECT 'inventario_fecha', i.inventario_snapshot_key
FROM marts.fct_inventario_snapshot AS i
LEFT JOIN marts.dim_fecha AS d ON i.fecha_key = d.fecha_key
WHERE d.fecha_key IS NULL
UNION ALL
SELECT 'inventario_producto', i.inventario_snapshot_key
FROM marts.fct_inventario_snapshot AS i
LEFT JOIN marts.dim_producto AS d ON i.producto_key = d.producto_key
WHERE d.producto_key IS NULL
UNION ALL
SELECT 'inventario_sucursal', i.inventario_snapshot_key
FROM marts.fct_inventario_snapshot AS i
LEFT JOIN marts.dim_sucursal AS d ON i.sucursal_key = d.sucursal_key
WHERE d.sucursal_key IS NULL
UNION ALL
SELECT 'devoluciones_fecha', r.devolucion_key::TEXT
FROM marts.fct_devoluciones AS r
LEFT JOIN marts.dim_fecha AS d ON r.fecha_key = d.fecha_key
WHERE d.fecha_key IS NULL
UNION ALL
SELECT 'devoluciones_producto', r.devolucion_key::TEXT
FROM marts.fct_devoluciones AS r
LEFT JOIN marts.dim_producto AS d ON r.producto_key = d.producto_key
WHERE d.producto_key IS NULL
UNION ALL
SELECT 'metas_fecha', m.meta_key
FROM marts.fct_metas_ventas AS m
LEFT JOIN marts.dim_fecha AS d ON m.periodo_key = d.fecha_key
WHERE d.fecha_key IS NULL
UNION ALL
SELECT 'metas_sucursal', m.meta_key
FROM marts.fct_metas_ventas AS m
LEFT JOIN marts.dim_sucursal AS d ON m.sucursal_key = d.sucursal_key
WHERE d.sucursal_key IS NULL
UNION ALL
SELECT 'precios_fecha', p.precio_proveedor_key
FROM marts.fct_precios_proveedor AS p
LEFT JOIN marts.dim_fecha AS d ON p.fecha_key = d.fecha_key
WHERE d.fecha_key IS NULL
UNION ALL
SELECT 'precios_producto', p.precio_proveedor_key
FROM marts.fct_precios_proveedor AS p
LEFT JOIN marts.dim_producto AS d ON p.producto_key = d.producto_key
WHERE d.producto_key IS NULL;
