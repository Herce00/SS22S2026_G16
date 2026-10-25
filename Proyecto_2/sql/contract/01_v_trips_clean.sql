-- =============================================================================
-- 01_v_trips_clean.sql
-- Propósito : Publicar la vista del contrato A-B, p2_contract.v_trips_clean,
--             con viajes limpios de 2022 y un esquema congelado para BigQuery ML.
-- Dueño     : Persona A (zona amarilla: el esquema solo cambia de común acuerdo).
-- Entradas  : bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022
-- Salidas   : ss2-g16-proyecto2.p2_contract.v_trips_clean (vista).
-- Fase 1    : el FROM lee la tabla pública y aplica los filtros de limpieza.
-- Fase 2    : A cambia el FROM a p2_a_trips.trips_2022_opt sin tocar nombres,
--             tipos ni orden de las columnas. B no modifica nada.
-- Referencia: Proyecto_2/specs/steering/architecture.md, sección "Contrato".
-- =============================================================================

CREATE OR REPLACE VIEW `ss2-g16-proyecto2.p2_contract.v_trips_clean`
OPTIONS (
  description = 'Contrato A-B (fase 1): viajes limpios de taxi amarillo NYC 2022. Esquema congelado: agregar, quitar, renombrar o cambiar el tipo de una columna requiere acuerdo de A y B.'
)
AS
SELECT
  -- Bloque 1: identificador determinista del viaje.
  -- Se calcula sobre los valores NUMERIC originales, antes de convertir a FLOAT64,
  -- para que el hash no dependa de la representación en coma flotante.
  FARM_FINGERPRINT(CONCAT(vendor_id,'|',CAST(pickup_datetime AS STRING),'|',CAST(dropoff_datetime AS STRING),'|',pickup_location_id,'|',dropoff_location_id,'|',CAST(trip_distance AS STRING),'|',CAST(total_amount AS STRING))) AS trip_id,

  -- Bloque 2: proveedor y marcas de tiempo originales.
  vendor_id,
  pickup_datetime,
  dropoff_datetime,

  -- Bloque 3: atributos de calendario derivados de la recogida.
  DATE(pickup_datetime)               AS pickup_date,
  EXTRACT(HOUR FROM pickup_datetime)  AS pickup_hour,
  EXTRACT(DAYOFWEEK FROM pickup_datetime) AS pickup_dow,   -- 1 = domingo
  EXTRACT(MONTH FROM pickup_datetime) AS pickup_month,

  -- Bloque 4: duración del viaje en minutos.
  TIMESTAMP_DIFF(dropoff_datetime, pickup_datetime, SECOND) / 60.0 AS trip_duration_min,

  -- Bloque 5: atributos del viaje. passenger_count conserva los nulos.
  passenger_count,
  CAST(trip_distance AS FLOAT64)      AS trip_distance,
  rate_code,
  payment_type,

  -- Bloque 6: montos. NUMERIC se convierte a FLOAT64 para BigQuery ML.
  CAST(fare_amount AS FLOAT64)        AS fare_amount,
  CAST(tip_amount AS FLOAT64)         AS tip_amount,
  CAST(tolls_amount AS FLOAT64)       AS tolls_amount,
  CAST(total_amount AS FLOAT64)       AS total_amount,

  -- Bloque 7: zonas de origen y destino.
  pickup_location_id,
  dropoff_location_id

-- Bloque 8: origen de la fase 1. En la fase 2 solo cambia esta línea.
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`

-- Bloque 9: filtros de limpieza, uno por línea.
WHERE
  -- Recogida dentro de 2022.
  pickup_datetime >= '2022-01-01' AND pickup_datetime < '2023-01-01'
  -- La llegada es posterior a la recogida.
  AND dropoff_datetime > pickup_datetime
  -- Duración máxima de 6 horas.
  AND TIMESTAMP_DIFF(dropoff_datetime, pickup_datetime, MINUTE) <= 360
  -- Distancia positiva y como máximo 100 millas.
  AND trip_distance > 0 AND trip_distance <= 100
  -- Tarifa base positiva.
  AND fare_amount > 0
  -- Monto total positivo.
  AND total_amount > 0
  -- Pasajeros nulos se conservan; si hay valor, debe estar entre 1 y 6.
  AND (passenger_count IS NULL OR passenger_count BETWEEN 1 AND 6);
