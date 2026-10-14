WITH ventas_mensuales AS (
    SELECT
        v.fecha_key / 100 AS periodo,
        v.sucursal_key,
        SUM(v.subtotal) AS ventas_reales,
        SUM(v.cantidad) AS unidades_reales
    FROM marts.fct_ventas_linea AS v
    GROUP BY v.fecha_key / 100, v.sucursal_key
)
SELECT
    m.periodo,
    s.nombre AS sucursal,
    m.meta_ventas,
    COALESCE(v.ventas_reales, 0) AS ventas_reales,
    m.meta_unidades,
    COALESCE(v.unidades_reales, 0) AS unidades_reales
FROM marts.fct_metas_ventas AS m
JOIN marts.dim_sucursal AS s
    ON m.sucursal_key = s.sucursal_key
LEFT JOIN ventas_mensuales AS v
    ON m.periodo_key / 100 = v.periodo
   AND m.sucursal_key = v.sucursal_key
ORDER BY m.periodo, s.nombre;
