-- Regla del contrato raw: venta_detalle.cantidad > 0.
-- La conversion acepta el cero, asi que esta prueba lo reporta. Devuelve las lineas que la incumplen.
SELECT id_detalle, cantidad
FROM {{ ref('fct_ventas_linea') }}
WHERE cantidad <= 0
