{{ config(
    materialized='incremental',
    unique_key='id_detalle',
    on_schema_change='sync_all_columns',
    post_hook=[
        "{{ clave_primaria('venta_linea_key') }}",
        "{{ clave_foranea('fecha_key', 'dim_fecha', 'fecha_key') }}",
        "{{ clave_foranea('cliente_key', 'dim_cliente', 'cliente_key') }}",
        "{{ clave_foranea('sucursal_key', 'dim_sucursal', 'sucursal_key') }}",
        "{{ clave_foranea('producto_key', 'dim_producto', 'producto_key') }}"
    ]
) }}

SELECT
    {{ clave_sustituta(['v.id_detalle']) }} AS venta_linea_key,
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
    v.importe_descuento,
    v._loaded_at
FROM {{ ref('int_ventas_linea') }} AS v
LEFT JOIN {{ ref('dim_cliente') }} AS c ON v.id_cliente = c.id_cliente
LEFT JOIN {{ ref('dim_sucursal') }} AS s ON v.id_sucursal = s.id_sucursal
LEFT JOIN {{ ref('dim_producto') }} AS p ON v.id_producto = p.id_producto
{% if is_incremental() %}
-- Solo procesa lo cargado despues de la ultima carga del hecho; con unique_key dbt reemplaza
-- (delete+insert) las filas que ya existian con el mismo id_detalle.
WHERE v._loaded_at > (SELECT COALESCE(MAX(_loaded_at), '1900-01-01'::TIMESTAMPTZ) FROM {{ this }})
{% endif %}
