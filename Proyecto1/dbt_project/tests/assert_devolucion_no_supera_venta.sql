-- Una devolucion no puede superar lo vendido del mismo producto en esa venta.
SELECT d.id_devolucion, d.id_venta, d.id_producto, d.cantidad AS cantidad_devuelta, v.cantidad_vendida
FROM {{ ref('int_devoluciones') }} AS d
LEFT JOIN (
    SELECT id_venta, id_producto, SUM(cantidad) AS cantidad_vendida
    FROM {{ ref('int_ventas_linea') }}
    GROUP BY id_venta, id_producto
) AS v
    ON v.id_venta = d.id_venta
   AND v.id_producto = d.id_producto
WHERE v.cantidad_vendida IS NULL
   OR d.cantidad > v.cantidad_vendida
