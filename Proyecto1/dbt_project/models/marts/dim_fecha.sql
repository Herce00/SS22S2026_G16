{{ config(
    post_hook=[
        "{{ clave_primaria('fecha_key') }}"
    ]
) }}

WITH limites AS (
    SELECT
        LEAST(
            COALESCE(MIN(fecha), DATE '9999-12-31'),
            COALESCE(MIN(fecha_corte), DATE '9999-12-31'),
            COALESCE(MIN(fecha_vigencia), DATE '9999-12-31'),
            COALESCE(MIN(fecha_inicio), DATE '9999-12-31'),
            COALESCE(MIN(fecha_alta), DATE '9999-12-31')
        ) AS fecha_minima,
        GREATEST(
            COALESCE(MAX(fecha), DATE '1900-01-01'),
            COALESCE(MAX(fecha_corte), DATE '1900-01-01'),
            COALESCE(MAX(fecha_vigencia), DATE '1900-01-01'),
            COALESCE(MAX(fecha_fin), DATE '1900-01-01'),
            COALESCE(MAX(fecha_alta), DATE '1900-01-01')
        ) AS fecha_maxima
    FROM (
        SELECT fecha, NULL::DATE AS fecha_corte, NULL::DATE AS fecha_vigencia,
               NULL::DATE AS fecha_inicio, NULL::DATE AS fecha_fin,
               NULL::DATE AS fecha_alta
        FROM {{ ref('stg_oltp__venta') }}
        UNION ALL
        SELECT NULL, fecha_corte, NULL, NULL, NULL, NULL
        FROM {{ ref('stg_archivos__inventario_bodega') }}
        UNION ALL
        SELECT NULL, NULL, fecha_vigencia, NULL, NULL, NULL
        FROM {{ ref('stg_archivos__proveedores_precios') }}
        UNION ALL
        SELECT NULL, NULL, NULL, fecha_inicio, fecha_fin, NULL
        FROM {{ ref('stg_archivos__promociones') }}
        UNION ALL
        SELECT NULL, NULL, NULL, NULL, NULL, fecha_alta
        FROM {{ ref('stg_oltp__cliente') }}
    ) fechas
),
calendario AS (
    SELECT generate_series(fecha_minima, fecha_maxima, INTERVAL '1 day')::DATE AS fecha
    FROM limites
    WHERE fecha_minima <= fecha_maxima
)
SELECT
    TO_CHAR(fecha, 'YYYYMMDD')::INTEGER AS fecha_key,
    fecha,
    EXTRACT(DAY FROM fecha)::INTEGER AS dia,
    EXTRACT(MONTH FROM fecha)::INTEGER AS mes,
    TO_CHAR(fecha, 'TMMonth') AS nombre_mes,
    EXTRACT(QUARTER FROM fecha)::INTEGER AS trimestre,
    EXTRACT(YEAR FROM fecha)::INTEGER AS anio,
    EXTRACT(WEEK FROM fecha)::INTEGER AS semana_anio,
    EXTRACT(ISODOW FROM fecha)::INTEGER IN (6, 7) AS es_fin_de_semana
FROM calendario
