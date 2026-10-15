-- Regla del contrato raw: venta_detalle.descuento entre 0 y 1.
-- NUMERIC(5,4) admite hasta 9.9999, asi que un descuento de 1.20 llega a marts y esta prueba lo reporta.
SELECT id_detalle, descuento
FROM {{ ref('fct_ventas_linea') }}
WHERE descuento NOT BETWEEN 0 AND 1
