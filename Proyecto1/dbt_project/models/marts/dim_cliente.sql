{{ config(
    post_hook=[
        "{{ clave_primaria('cliente_key') }}"
    ]
) }}

SELECT
    {{ clave_sustituta(['id_cliente']) }} AS cliente_key,
    id_cliente,
    nit,
    nombre,
    tipo_cliente,
    municipio,
    departamento,
    fecha_alta
FROM {{ ref('stg_oltp__cliente') }}
