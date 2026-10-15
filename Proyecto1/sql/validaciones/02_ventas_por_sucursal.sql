-- Pregunta: cuanto vendio cada sucursal?
-- Regla de ingresos: solo cuentan las ventas con estado COMPLETADA. Las anuladas y las
-- pendientes no son ingreso; se muestran aparte para poder conciliarlas.
-- Resultado esperado: una fila por sucursal con ventas, unidades e ingresos de ventas completadas,
-- y la cantidad de ventas anuladas y pendientes que quedaron fuera.
SELECT
    s.nombre AS sucursal,
    COUNT(DISTINCT v.id_venta) FILTER (WHERE v.estado = 'COMPLETADA') AS ventas,
    SUM(v.cantidad) FILTER (WHERE v.estado = 'COMPLETADA') AS unidades,
    SUM(v.subtotal) FILTER (WHERE v.estado = 'COMPLETADA') AS ingresos,
    COUNT(DISTINCT v.id_venta) FILTER (WHERE v.estado = 'ANULADA') AS ventas_anuladas,
    COUNT(DISTINCT v.id_venta) FILTER (WHERE v.estado = 'PENDIENTE') AS ventas_pendientes
FROM marts.fct_ventas_linea AS v
JOIN marts.dim_sucursal AS s
    ON v.sucursal_key = s.sucursal_key
GROUP BY s.sucursal_key, s.nombre
ORDER BY ingresos DESC;
