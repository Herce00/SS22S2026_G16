SELECT
    {{ convertir_seguro('id_proveedor', 'INTEGER') }} AS id_proveedor,
    NULLIF(TRIM(proveedor), '') AS proveedor,
    {{ convertir_seguro('id_producto', 'INTEGER') }} AS id_producto,
    {{ convertir_seguro('costo_proveedor', 'NUMERIC(12,2)') }} AS costo_proveedor,
    {{ convertir_seguro('plazo_dias', 'INTEGER') }} AS plazo_dias,
    {{ convertir_seguro('fecha_vigencia', 'DATE') }} AS fecha_vigencia,
    _loaded_at
FROM {{ source('archivos', 'proveedores_precios') }}
