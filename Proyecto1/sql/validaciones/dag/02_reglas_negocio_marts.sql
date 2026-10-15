-- Pregunta: algun hecho incumple una regla de negocio que si puede ocurrir con los datos tipados?
-- Resultado esperado: cero filas.
-- Staging deja en NULL todo valor negativo o invalido, asi que aqui no se buscan negativos:
-- se buscan nulos en las medidas, cantidades en cero, descuentos fuera de 0 a 1 y
-- minimos de stock mayores que el maximo.
SELECT 'ventas_cantidad_no_positiva' AS validacion, venta_linea_key AS clave
FROM marts.fct_ventas_linea
WHERE COALESCE(cantidad, 0) <= 0
UNION ALL
SELECT 'ventas_subtotal_nulo', venta_linea_key
FROM marts.fct_ventas_linea
WHERE subtotal IS NULL
UNION ALL
SELECT 'ventas_descuento_fuera_de_rango', venta_linea_key
FROM marts.fct_ventas_linea
WHERE descuento NOT BETWEEN 0 AND 1
UNION ALL
SELECT 'inventario_stock_nulo', inventario_snapshot_key
FROM marts.fct_inventario_snapshot
WHERE stock_disponible IS NULL
   OR stock_minimo IS NULL
   OR stock_maximo IS NULL
UNION ALL
SELECT 'inventario_minimo_mayor_maximo', inventario_snapshot_key
FROM marts.fct_inventario_snapshot
WHERE stock_minimo > stock_maximo
UNION ALL
SELECT 'devolucion_cantidad_no_positiva', devolucion_key::TEXT
FROM marts.fct_devoluciones
WHERE COALESCE(cantidad, 0) <= 0
UNION ALL
SELECT 'metas_valores_nulos', meta_key
FROM marts.fct_metas_ventas
WHERE meta_ventas IS NULL
   OR meta_unidades IS NULL
UNION ALL
SELECT 'precios_costo_nulo', precio_proveedor_key
FROM marts.fct_precios_proveedor
WHERE costo_proveedor IS NULL;
