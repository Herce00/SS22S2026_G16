SELECT
    i.fecha_corte,
    i.id_sucursal,
    i.id_producto,
    i.lote,
    i.fecha_vencimiento,
    i.stock_disponible,
    i.stock_minimo,
    i.stock_maximo,
    GREATEST(i.stock_minimo - i.stock_disponible, 0) AS stock_faltante,
    GREATEST(i.stock_disponible - i.stock_maximo, 0) AS stock_sobrante,
    i.stock_disponible < i.stock_minimo AS esta_bajo_minimo,
    i.stock_disponible > i.stock_maximo AS esta_sobre_maximo,
    i._loaded_at
FROM {{ ref('stg_archivos__inventario_bodega') }} AS i
