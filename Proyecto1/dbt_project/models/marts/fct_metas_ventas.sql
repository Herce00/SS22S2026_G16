SELECT
    MD5(CONCAT_WS('|', m.periodo, m.id_sucursal)) AS meta_key,
    TO_CHAR(m.periodo_fecha, 'YYYYMMDD')::INTEGER AS periodo_key,
    m.periodo,
    s.sucursal_key,
    m.meta_ventas,
    m.meta_unidades
FROM {{ ref('int_metas_ventas') }} AS m
LEFT JOIN {{ ref('dim_sucursal') }} AS s ON m.id_sucursal = s.id_sucursal
