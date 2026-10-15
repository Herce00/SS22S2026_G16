{{ config(
    post_hook=[
        "{{ clave_primaria('sucursal_key') }}"
    ]
) }}

SELECT
    {{ clave_sustituta(['id_sucursal']) }} AS sucursal_key,
    id_sucursal,
    nombre,
    ciudad,
    departamento
FROM {{ ref('stg_oltp__sucursal') }}
