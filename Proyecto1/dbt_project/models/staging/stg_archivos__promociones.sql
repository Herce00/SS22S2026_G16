SELECT
    {{ convertir_seguro('id_promocion', 'INTEGER') }} AS id_promocion,
    NULLIF(TRIM(nombre), '') AS nombre,
    {{ convertir_seguro('fecha_inicio', 'DATE') }} AS fecha_inicio,
    {{ convertir_seguro('fecha_fin', 'DATE') }} AS fecha_fin,
    {{ convertir_seguro('id_categoria', 'INTEGER') }} AS id_categoria,
    {{ convertir_seguro('porcentaje_descuento', 'NUMERIC(5,4)') }} AS porcentaje_descuento,
    _loaded_at
FROM {{ source('archivos', 'promociones') }}
