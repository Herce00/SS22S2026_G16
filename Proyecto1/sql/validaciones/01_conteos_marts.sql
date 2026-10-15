-- Pregunta: cuantas filas tiene cada tabla de marts?
-- Resultado esperado: 12 filas, una por dimension y por hecho, con los conteos de la ultima
-- ejecucion del DAG (se guardan en evidencia/marts_conteos.txt).
SELECT 'dim_fecha' AS tabla, COUNT(*) AS filas
FROM marts.dim_fecha
UNION ALL
SELECT 'dim_sucursal', COUNT(*)
FROM marts.dim_sucursal
UNION ALL
SELECT 'dim_categoria', COUNT(*)
FROM marts.dim_categoria
UNION ALL
SELECT 'dim_marca', COUNT(*)
FROM marts.dim_marca
UNION ALL
SELECT 'dim_producto', COUNT(*)
FROM marts.dim_producto
UNION ALL
SELECT 'dim_cliente', COUNT(*)
FROM marts.dim_cliente
UNION ALL
SELECT 'dim_promocion', COUNT(*)
FROM marts.dim_promocion
UNION ALL
SELECT 'fct_ventas_linea', COUNT(*)
FROM marts.fct_ventas_linea
UNION ALL
SELECT 'fct_inventario_snapshot', COUNT(*)
FROM marts.fct_inventario_snapshot
UNION ALL
SELECT 'fct_devoluciones', COUNT(*)
FROM marts.fct_devoluciones
UNION ALL
SELECT 'fct_metas_ventas', COUNT(*)
FROM marts.fct_metas_ventas
UNION ALL
SELECT 'fct_precios_proveedor', COUNT(*)
FROM marts.fct_precios_proveedor;
