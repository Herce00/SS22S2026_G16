SELECT
    TO_DATE(m.periodo || '-01', 'YYYY-MM-DD') AS periodo_fecha,
    m.periodo,
    m.id_sucursal,
    m.meta_ventas,
    m.meta_unidades,
    m._loaded_at
FROM {{ ref('stg_archivos__metas_ventas') }} AS m
