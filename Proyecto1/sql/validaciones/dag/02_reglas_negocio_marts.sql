SELECT 'ventas_cantidad_no positiva' AS validacion, venta_linea_key
FROM marts.fct_ventas_linea
WHERE cantidad <= 0
UNION ALL
SELECT 'ventas_subtotal_negativo', venta_linea_key
FROM marts.fct_ventas_linea
WHERE subtotal < 0
UNION ALL
SELECT 'inventario_stock_negativo', inventario_snapshot_key
FROM marts.fct_inventario_snapshot
WHERE stock_disponible < 0
   OR stock_minimo < 0
   OR stock_maximo < 0
UNION ALL
SELECT 'devolucion_cantidad_no positiva', devolucion_key::TEXT
FROM marts.fct_devoluciones
WHERE cantidad <= 0;
