{{ config(
    materialized='incremental',
    unique_key='id_detalle',
    on_schema_change='sync_all_columns'
) }}

SELECT
    MD5(v.id_detalle::TEXT) AS venta_linea_key,
    v.id_detalle,
    v.id_venta,
    TO_CHAR(v.fecha, 'YYYYMMDD')::INTEGER AS fecha_key,
    c.cliente_key,
    s.sucursal_key,
    p.producto_key,
    v.canal,
    v.metodo_pago,
    v.estado,
    v.cantidad,
    v.precio_unitario,
    v.descuento,
    v.subtotal,
    v.importe_bruto,
    v.importe_descuento
FROM {{ ref('int_ventas_linea') }} AS v
LEFT JOIN {{ ref('dim_cliente') }} AS c ON v.id_cliente = c.id_cliente
LEFT JOIN {{ ref('dim_sucursal') }} AS s ON v.id_sucursal = s.id_sucursal
LEFT JOIN {{ ref('dim_producto') }} AS p ON v.id_producto = p.id_producto
{% if is_incremental() %}
WHERE NOT EXISTS (
    SELECT 1
    FROM {{ this }} AS existente
    WHERE existente.id_detalle = v.id_detalle
)
{% endif %}
