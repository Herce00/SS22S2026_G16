-- Una meta mensual de ventas o de unidades debe ser mayor que cero.
SELECT periodo, id_sucursal, meta_ventas, meta_unidades
FROM {{ ref('int_metas_ventas') }}
WHERE meta_ventas <= 0
   OR meta_unidades <= 0
