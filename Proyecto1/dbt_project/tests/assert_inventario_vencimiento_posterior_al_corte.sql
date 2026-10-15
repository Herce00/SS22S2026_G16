-- Un lote no puede vencer antes de la fecha de corte del snapshot que lo registra.
SELECT fecha_corte, id_sucursal, id_producto, lote, fecha_vencimiento
FROM {{ ref('int_inventario_snapshot') }}
WHERE fecha_vencimiento < fecha_corte
