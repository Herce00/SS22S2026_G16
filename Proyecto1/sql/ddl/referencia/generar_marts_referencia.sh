#!/usr/bin/env bash
# Regenera 03_marts_referencia.sql desde la base. Ejecutar desde Proyecto1/ despues de correr el DAG:
#   bash sql/ddl/referencia/generar_marts_referencia.sh
set -euo pipefail
set -a; . ./.env; set +a
salida="sql/ddl/referencia/03_marts_referencia.sql"
{
  cat <<ENCABEZADO
-- DDL de referencia del schema marts: referencia generada, solo documentacion.
-- Fecha de generacion: $(date +%Y-%m-%d)
-- Comando: pg_dump --schema-only --schema=marts --no-owner --no-privileges
-- Origen: la base ${DW_DB} despues de una ejecucion del DAG sgfood_elt.
-- dbt crea y recrea estas tablas y restricciones en cada ejecucion (dbt run).
-- Este archivo no se ejecuta en la inicializacion del DW: vive en una subcarpeta que
-- /docker-entrypoint-initdb.d no recorre, porque crearia tablas que dbt espera crear.
-- ---- fin del encabezado ----
ENCABEZADO
  docker compose exec -T dw pg_dump -U "${DW_USER}" -d "${DW_DB}" \
    --schema-only --schema=marts --no-owner --no-privileges \
    | grep -v -e '^[\]restrict' -e '^[\]unrestrict'
} > "${salida}"
