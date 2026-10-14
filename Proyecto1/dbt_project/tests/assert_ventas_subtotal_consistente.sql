SELECT
    id_detalle,
    subtotal,
    importe_bruto,
    importe_descuento
FROM {{ ref('fct_ventas_linea') }}
WHERE subtotal IS NULL
   OR importe_bruto IS NULL
   OR importe_descuento IS NULL
   OR ABS(subtotal - (importe_bruto - importe_descuento)) > 0.01
