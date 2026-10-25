-- =============================================================================
-- a_01_tablas_derivadas.sql
-- Propósito : Crear las tablas derivadas de A en p2_a_trips: una optimizada
--             (partición diaria y clustering por ubicaciones) y una estándar
--             (sin partición ni clustering) para la comparación de rendimiento.
-- Dueño     : Persona A (zona verde).
-- Entradas  : bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022
-- Salidas   : ss2-g16-proyecto2.p2_a_trips.trips_2022_opt (tabla)
--             ss2-g16-proyecto2.p2_a_trips.trips_2022_std (tabla)
-- Decisiones: O1: la limpieza vive aquí, al construir trips_2022_opt desde la
--             tabla pública, con las mismas expresiones y filtros que la vista
--             del contrato en fase 1. Así la fase 2 de la vista puede leer de
--             trips_2022_opt sin una dependencia circular.
--             O2: trips_2022_std es una copia de trips_2022_opt sin partición
--             ni clustering; solo cambia el layout físico.
-- Evidencia : Proyecto_2/evidencia/04_tablas_derivadas.txt
-- Referencia: odd/tasks/p2-a-optimizacion.md y
--             Proyecto_2/specs/steering/architecture.md, sección "Contrato".
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Bloque 1: tabla optimizada trips_2022_opt.
-- Partición diaria por DATE(pickup_datetime) (válida sobre TIMESTAMP) y
-- clustering por las zonas de origen y destino (decisión O3). Sin
-- require_partition_filter (decisión O4). Las columnas, su orden, trip_id y los
-- 7 filtros son copia exacta de Proyecto_2/sql/contract/01_v_trips_clean.sql.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
PARTITION BY DATE(pickup_datetime)
CLUSTER BY pickup_location_id, dropoff_location_id
OPTIONS (
  description = 'Viajes limpios de taxi amarillo NYC 2022 (misma lógica que el contrato en fase 1). Partición diaria por DATE(pickup_datetime) y clustering por pickup_location_id, dropoff_location_id. Fuente de la fase 2 de p2_contract.v_trips_clean.'
)
AS
SELECT
  -- Identificador determinista del viaje, calculado sobre los valores NUMERIC originales.
  FARM_FINGERPRINT(CONCAT(vendor_id,'|',CAST(pickup_datetime AS STRING),'|',CAST(dropoff_datetime AS STRING),'|',pickup_location_id,'|',dropoff_location_id,'|',CAST(trip_distance AS STRING),'|',CAST(total_amount AS STRING))) AS trip_id,

  -- Proveedor y marcas de tiempo originales.
  vendor_id,
  pickup_datetime,
  dropoff_datetime,

  -- Atributos de calendario derivados de la recogida.
  DATE(pickup_datetime)               AS pickup_date,
  EXTRACT(HOUR FROM pickup_datetime)  AS pickup_hour,
  EXTRACT(DAYOFWEEK FROM pickup_datetime) AS pickup_dow,   -- 1 = domingo
  EXTRACT(MONTH FROM pickup_datetime) AS pickup_month,

  -- Duración del viaje en minutos.
  TIMESTAMP_DIFF(dropoff_datetime, pickup_datetime, SECOND) / 60.0 AS trip_duration_min,

  -- Atributos del viaje. passenger_count conserva los nulos.
  passenger_count,
  CAST(trip_distance AS FLOAT64)      AS trip_distance,
  rate_code,
  payment_type,

  -- Montos. NUMERIC se convierte a FLOAT64 para BigQuery ML.
  CAST(fare_amount AS FLOAT64)        AS fare_amount,
  CAST(tip_amount AS FLOAT64)         AS tip_amount,
  CAST(tolls_amount AS FLOAT64)       AS tolls_amount,
  CAST(total_amount AS FLOAT64)       AS total_amount,

  -- Zonas de origen y destino.
  pickup_location_id,
  dropoff_location_id

FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`

-- Filtros de limpieza, uno por línea.
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


-- -----------------------------------------------------------------------------
-- Bloque 2: tabla estándar trips_2022_std.
-- Mismos datos que trips_2022_opt, sin partición ni clustering (decisión O2).
-- Es la línea base de la comparación de rendimiento.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `ss2-g16-proyecto2.p2_a_trips.trips_2022_std`
OPTIONS (
  description = 'Copia de trips_2022_opt sin partición ni clustering. Línea base para la comparación de rendimiento estándar vs optimizada.'
)
AS
SELECT * FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`;


-- -----------------------------------------------------------------------------
-- Bloque 3: consultas de metadatos y verificación.
-- Están comentadas para que el script solo cree las tablas. Cada una se ejecuta
-- por separado y su salida se guarda en Proyecto_2/evidencia/04_tablas_derivadas.txt.
-- -----------------------------------------------------------------------------

-- (a) ¿Cuántas filas tiene cada tabla? Esperado: 34,796,108 en ambas.
-- SELECT 'trips_2022_opt' AS table_name, COUNT(*) AS row_count
-- FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt`
-- UNION ALL
-- SELECT 'trips_2022_std', COUNT(*)
-- FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_std`;

-- (b) ¿Cuántas filas y bytes lógicos almacena cada tabla según los metadatos?
--     Esperado: 34,796,108 filas en ambas y un tamaño lógico similar.
-- SELECT table_id, row_count AS total_rows, size_bytes AS total_logical_bytes,
--        ROUND(size_bytes / POW(1024, 3), 2) AS total_logical_gib
-- FROM `ss2-g16-proyecto2.p2_a_trips.__TABLES__`
-- WHERE table_id IN ('trips_2022_opt', 'trips_2022_std')
-- ORDER BY table_id;

-- (c) ¿Cuántas particiones tiene trips_2022_opt y cuál es su rango?
--     Esperado: unas 335 particiones diarias, más una __NULL__ si existiera.
-- SELECT COUNT(*) AS partition_count,
--        MIN(partition_id) AS min_partition_id,
--        MAX(partition_id) AS max_partition_id,
--        SUM(total_rows) AS total_rows
-- FROM `ss2-g16-proyecto2.p2_a_trips.INFORMATION_SCHEMA.PARTITIONS`
-- WHERE table_name = 'trips_2022_opt';

-- (d) ¿Qué columnas de clustering y de partición tiene cada tabla?
--     Esperado: opt con pickup_location_id = 1, dropoff_location_id = 2 y
--     partición por pickup_datetime; std sin filas.
-- SELECT table_name, column_name, clustering_ordinal_position, is_partitioning_column
-- FROM `ss2-g16-proyecto2.p2_a_trips.INFORMATION_SCHEMA.COLUMNS`
-- WHERE table_name IN ('trips_2022_opt', 'trips_2022_std')
--   AND (clustering_ordinal_position IS NOT NULL OR is_partitioning_column = 'YES')
-- ORDER BY table_name, clustering_ordinal_position;

-- (e) ¿trips_2022_opt tiene el mismo contenido que la vista del contrato?
--     Se compara la huella de la fila completa:
--     BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(t))) sobre las 19 columnas.
--     TO_JSON_STRING depende de los nombres y del orden de las columnas; opt y
--     la vista tienen las mismas 19 columnas en el mismo orden (verificado en
--     INFORMATION_SCHEMA.COLUMNS), así que las huellas son comparables.
--     Desde la fase 2 la vista proyecta opt, así que esta consulta compara opt
--     consigo mismo. La comprobación con valor real es la línea base: la huella
--     (f) de la vista en fase 1 frente a la huella de opt. Ambas valen
--     2642667349256316066 (Proyecto_2/evidencia/06_contrato_fase2.txt).
--     Esperado: row_count y row_fp iguales en las dos filas.
-- SELECT 'trips_2022_opt' AS source, COUNT(*) AS row_count,
--        BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS row_fp
-- FROM `ss2-g16-proyecto2.p2_a_trips.trips_2022_opt` AS t
-- UNION ALL
-- SELECT 'v_trips_clean', COUNT(*), BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(t)))
-- FROM `ss2-g16-proyecto2.p2_contract.v_trips_clean` AS t;
