SELECT
    s.nombre AS sucursal,
    COUNT(DISTINCT v.id_venta) AS ventas,
    SUM(v.cantidad) AS unidades,
    SUM(v.subtotal) AS ingresos
FROM marts.fct_ventas_linea AS v
JOIN marts.dim_sucursal AS s
    ON v.sucursal_key = s.sucursal_key
GROUP BY s.sucursal_key, s.nombre
ORDER BY ingresos DESC;
