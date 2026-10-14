SELECT
    ROW_NUMBER() OVER (ORDER BY p.id_producto)::INTEGER AS producto_key,
    p.id_producto,
    p.sku,
    p.nombre,
    c.categoria_key,
    m.marca_key,
    p.unidad_medida,
    p.costo_base,
    p.precio_lista,
    p.activo
FROM {{ ref('stg_oltp__producto') }} AS p
LEFT JOIN {{ ref('dim_categoria') }} AS c
    ON p.id_categoria = c.id_categoria
LEFT JOIN {{ ref('dim_marca') }} AS m
    ON p.id_marca = m.id_marca
