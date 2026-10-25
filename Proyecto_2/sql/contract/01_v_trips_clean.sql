-- =============================================================================
-- 01_v_trips_clean.sql
-- Propósito : Publicar la vista del contrato A-B, p2_contract.v_trips_clean,
--             con viajes limpios de 2022 y un esquema congelado para BigQuery ML.
-- Dueño     : Persona A (zona amarilla: el esquema solo cambia de común acuerdo).
-- Entradas  : ss2-g16-proyecto2.p2_a_trips.trips_2022_opt
-- Salidas   : ss2-g16-proyecto2.p2_contract.v_trips_clean (vista).
-- Fase 2    : versión activa desde 2026-10-25. La vista es una proyección simple
--             de p2_a_trips.trips_2022_opt, que ya contiene trip_id, las
--             columnas derivadas y los 7 filtros de limpieza (decisión O1 de
--             odd/tasks/p2-a-optimizacion.md). Nombres, tipos y orden de las
--             19 columnas no cambian. B no modifica nada.
-- Fase 1    : la vista leía la tabla pública
--             bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022 y
--             aplicaba allí los filtros. Esa versión está en el historial de git.
-- Evidencia : Proyecto_2/evidencia/06_contrato_fase2.txt (fase 1 frente a fase 2).
-- Referencia: Proyecto_2/specs/steering/architecture.md, sección "Contrato".
-- =============================================================================

CREATE OR REPLACE VIEW `ss2-g16-proyecto2.p2_contract.v_trips_clean`
OPTIONS (
  description = 'Contrato A-B (fase 2): viajes limpios de taxi amarillo NYC 2022, proyectados desde p2_a_trips.trips_2022_opt (partición diaria y clustering por ubicaciones). Esquema congelado: agregar, quitar, renombrar o cambiar el tipo de una columna requiere acuerdo de A y B.'
)
AS
SELECT
  -- Bloque 1: identificador determinista del viaje, ya calculado en trips_2022_opt.
  trip_id,

  -- Bloque 2: proveedor y marcas de tiempo originales.
  vendor_id,
  pickup_datetime,
  dropoff_datetime,

  -- Bloque 3: atributos de calendario derivados de la recogida.
  pickup_date,
  pickup_hour,
  pickup_dow,          -- 1 = domingo
  pickup_month,

  -- Bloque 4: duración del viaje en minutos.
  trip_duration_min,

  -- Bloque 5: atributos del viaje. passenger_count conserva los nulos.
  passenger_count,
  trip_distance,
  rate_code,
  payment_type,

  -- Bloque 6: montos, ya convertidos a FLOAT64 en trips_2022_opt.
  fare_amount,
  tip_amount,
  tolls_amount,
  total_amount,

  -- Bloque 7: zonas de origen y destino.
  pickup_location_id,
  dropoff_location_id

-- Bloque 8: origen de la fase 2. Sin filtros: la limpieza vive en trips_2022_opt.
FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`;
