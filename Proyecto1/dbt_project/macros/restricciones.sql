{#- Restricciones fisicas de marts, creadas con post_hook.

    Son idempotentes: cada una elimina la restriccion si existe y la vuelve a crear. Cuando dbt
    reconstruye una dimension, el DROP ... CASCADE elimina las claves foraneas que la referencian;
    los hechos se construyen despues (por ref) y las vuelven a crear.

    Uso en el config de un modelo:
      post_hook=[clave_primaria('cliente_key')]
      post_hook=[clave_primaria('venta_linea_key'), clave_foranea('cliente_key', 'dim_cliente', 'cliente_key')]
-#}
{#- dbt reconstruye una tabla renombrando la anterior a <tabla>__dbt_backup y la elimina despues del commit.
    El indice de su clave primaria conserva el nombre pk_<tabla>, asi que se elimina primero para que
    el nombre quede libre. CASCADE retira las claves foraneas que apuntaban a la tabla anterior. -#}
{% macro clave_primaria(columna) -%}
    ALTER TABLE IF EXISTS {{ this.schema }}.{{ this.identifier ~ '__dbt_backup' }} DROP CONSTRAINT IF EXISTS pk_{{ this.identifier }} CASCADE;
    ALTER TABLE {{ this }} DROP CONSTRAINT IF EXISTS pk_{{ this.identifier }};
    ALTER TABLE {{ this }} ADD CONSTRAINT pk_{{ this.identifier }} PRIMARY KEY ({{ columna }})
{%- endmacro %}

{% macro clave_foranea(columna, dimension, columna_dimension) -%}
    ALTER TABLE {{ this }} DROP CONSTRAINT IF EXISTS fk_{{ this.identifier }}_{{ columna }};
    ALTER TABLE {{ this }} ADD CONSTRAINT fk_{{ this.identifier }}_{{ columna }}
        FOREIGN KEY ({{ columna }}) REFERENCES {{ ref(dimension) }} ({{ columna_dimension }})
{%- endmacro %}
