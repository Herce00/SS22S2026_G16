SELECT
    -- periodo AAAA-MM: queda en NULL si el mes no existe (por ejemplo 2026-13)
    TO_CHAR({{ convertir_seguro("TRIM(periodo) || '-01'", 'DATE') }}, 'YYYY-MM') AS periodo,
    {{ convertir_seguro('id_sucursal', 'INTEGER') }} AS id_sucursal,
    {{ convertir_seguro('meta_ventas', 'NUMERIC(14,2)') }} AS meta_ventas,
    {{ convertir_seguro('meta_unidades', 'INTEGER') }} AS meta_unidades,
    _loaded_at
FROM {{ source('archivos', 'metas_ventas') }}
