-- ============================================================================
-- SCRIPT DDL: MODELO MULTIDIMENSIONAL EN ESQUEMA ESTRELLA (STAR SCHEMA)
-- Base de Datos: VuelosDW (Microsoft SQL Server)
-- Curso: Seminario de Sistemas 2 - 2do Semestre 2026 - Grupo 16
-- Integrantes:
--   - César Rolando Hernández Palacios (202000806)
--   - Keneth Willard Lopez Ovalle (202100106)
-- ============================================================================

-- 1. Creación de la Base de Datos Data Warehouse
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'VuelosDW')
BEGIN
    CREATE DATABASE VuelosDW;
    PRINT '>> Base de datos VuelosDW creada exitosamente.';
END
GO

USE VuelosDW;
GO

-- ============================================================================
-- 2. ELIMINACIÓN DE TABLAS PREVIAS (ORDEN INVERSO DE DEPENDENCIAS)
-- ============================================================================
IF OBJECT_ID(N'dbo.fact_vuelo_pasaje', N'U') IS NOT NULL DROP TABLE dbo.fact_vuelo_pasaje;
IF OBJECT_ID(N'dbo.dim_canal_pago', N'U') IS NOT NULL DROP TABLE dbo.dim_canal_pago;
IF OBJECT_ID(N'dbo.dim_aeronave', N'U') IS NOT NULL DROP TABLE dbo.dim_aeronave;
IF OBJECT_ID(N'dbo.dim_pasajero', N'U') IS NOT NULL DROP TABLE dbo.dim_pasajero;
IF OBJECT_ID(N'dbo.dim_aeropuerto', N'U') IS NOT NULL DROP TABLE dbo.dim_aeropuerto;
IF OBJECT_ID(N'dbo.dim_aerolinea', N'U') IS NOT NULL DROP TABLE dbo.dim_aerolinea;
IF OBJECT_ID(N'dbo.dim_fecha', N'U') IS NOT NULL DROP TABLE dbo.dim_fecha;
GO

-- ============================================================================
-- 3. CREACIÓN DE TABLAS DE DIMENSIONES
-- ============================================================================

-- Dimensión 1: Fecha (Dimensión Conforme)
CREATE TABLE dbo.dim_fecha (
    id_fecha        INT NOT NULL,              -- Formato YYYYMMDD (ej. 20240120)
    fecha           DATE NOT NULL,
    anio            INT NOT NULL,
    trimestre       INT NOT NULL,
    mes             INT NOT NULL,
    nombre_mes      VARCHAR(20) NOT NULL,
    dia             INT NOT NULL,
    dia_semana      VARCHAR(20) NOT NULL,
    es_fin_semana   INT NOT NULL,              -- 1: Fin de semana, 0: Día de semana
    CONSTRAINT PK_dim_fecha PRIMARY KEY CLUSTERED (id_fecha)
);
GO

-- Dimensión 2: Aerolínea
CREATE TABLE dbo.dim_aerolinea (
    id_aerolinea     INT NOT NULL,
    codigo_aerolinea VARCHAR(10) NOT NULL,
    nombre_aerolinea VARCHAR(100) NOT NULL,
    CONSTRAINT PK_dim_aerolinea PRIMARY KEY CLUSTERED (id_aerolinea),
    CONSTRAINT UQ_dim_aerolinea_codigo UNIQUE (codigo_aerolinea)
);
GO

-- Dimensión 3: Aeropuerto
CREATE TABLE dbo.dim_aeropuerto (
    id_aeropuerto     INT NOT NULL,
    codigo_aeropuerto VARCHAR(10) NOT NULL,     -- Código IATA (ej. GUA, LAX, MIA)
    CONSTRAINT PK_dim_aeropuerto PRIMARY KEY CLUSTERED (id_aeropuerto),
    CONSTRAINT UQ_dim_aeropuerto_codigo UNIQUE (codigo_aeropuerto)
);
GO

-- Dimensión 4: Pasajero
CREATE TABLE dbo.dim_pasajero (
    id_pasajero   INT NOT NULL,
    passenger_id  VARCHAR(50) NOT NULL,         -- Clave natural del sistema origen
    genero        VARCHAR(10) NOT NULL,         -- 'F', 'M', 'X'
    edad          INT NOT NULL,
    nacionalidad  VARCHAR(100) NOT NULL,
    CONSTRAINT PK_dim_pasajero PRIMARY KEY CLUSTERED (id_pasajero),
    CONSTRAINT UQ_dim_pasajero_natural UNIQUE (passenger_id)
);
GO

-- Dimensión 5: Aeronave
CREATE TABLE dbo.dim_aeronave (
    id_aeronave   INT NOT NULL,
    tipo_aeronave VARCHAR(50) NOT NULL,         -- Código de aeronave (ej. B738, A320)
    CONSTRAINT PK_dim_aeronave PRIMARY KEY CLUSTERED (id_aeronave),
    CONSTRAINT UQ_dim_aeronave_tipo UNIQUE (tipo_aeronave)
);
GO

-- Dimensión 6: Canal y Método de Pago
CREATE TABLE dbo.dim_canal_pago (
    id_canal_pago INT NOT NULL,
    canal_venta   VARCHAR(50) NOT NULL,         -- APP, WEB, AEROPUERTO, AGENCIA, CALL_CENTER
    metodo_pago   VARCHAR(50) NOT NULL,         -- TARJETA, EFECTIVO, PAYPAL, TRANSFERENCIA, PUNTOS
    CONSTRAINT PK_dim_canal_pago PRIMARY KEY CLUSTERED (id_canal_pago),
    CONSTRAINT UQ_dim_canal_pago_comb UNIQUE (canal_venta, metodo_pago)
);
GO

-- ============================================================================
-- 4. CREACIÓN DE LA TABLA DE HECHOS (FACT TABLE)
-- ============================================================================
CREATE TABLE dbo.fact_vuelo_pasaje (
    id_fact                 BIGINT NOT NULL,
    record_id               INT NOT NULL,
    flight_number           VARCHAR(20) NOT NULL,
    id_aerolinea            INT NOT NULL,
    id_aeropuerto_origen    INT NOT NULL,
    id_aeropuerto_destino   INT NOT NULL,
    id_pasajero             INT NOT NULL,
    id_aeronave             INT NOT NULL,
    id_canal_pago           INT NOT NULL,
    id_fecha_salida         INT NOT NULL,
    id_fecha_reserva        INT NOT NULL,
    estado_vuelo            VARCHAR(30) NOT NULL,     -- ON_TIME, DELAYED, CANCELLED, DIVERTED
    clase_cabina            VARCHAR(30) NOT NULL,     -- ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
    asiento                 VARCHAR(20) NULL,         -- Nullable en vuelos cancelados
    fecha_salida            DATETIME2 NOT NULL,
    fecha_llegada           DATETIME2 NULL,           -- Nullable en vuelos cancelados
    duracion_min            FLOAT NULL,               -- Nullable en vuelos cancelados
    demora_min              FLOAT NULL,               -- Nullable en vuelos cancelados
    precio_boleto_original  FLOAT NOT NULL,
    moneda_original         VARCHAR(10) NOT NULL,
    precio_boleto_usd       DECIMAL(10, 2) NOT NULL,  -- Métrica financiera normalizada en USD
    total_maletas           INT NOT NULL,
    maletas_facturadas      INT NOT NULL,

    -- Clave Primaria
    CONSTRAINT PK_fact_vuelo_pasaje PRIMARY KEY CLUSTERED (id_fact),

    -- Claves Foráneas (Integridad Referencial)
    CONSTRAINT FK_fact_aerolinea FOREIGN KEY (id_aerolinea)
        REFERENCES dbo.dim_aerolinea (id_aerolinea),

    CONSTRAINT FK_fact_aeropuerto_origen FOREIGN KEY (id_aeropuerto_origen)
        REFERENCES dbo.dim_aeropuerto (id_aeropuerto),

    CONSTRAINT FK_fact_aeropuerto_destino FOREIGN KEY (id_aeropuerto_destino)
        REFERENCES dbo.dim_aeropuerto (id_aeropuerto),

    CONSTRAINT FK_fact_pasajero FOREIGN KEY (id_pasajero)
        REFERENCES dbo.dim_pasajero (id_pasajero),

    CONSTRAINT FK_fact_aeronave FOREIGN KEY (id_aeronave)
        REFERENCES dbo.dim_aeronave (id_aeronave),

    CONSTRAINT FK_fact_canal_pago FOREIGN KEY (id_canal_pago)
        REFERENCES dbo.dim_canal_pago (id_canal_pago),

    CONSTRAINT FK_fact_fecha_salida FOREIGN KEY (id_fecha_salida)
        REFERENCES dbo.dim_fecha (id_fecha),

    CONSTRAINT FK_fact_fecha_reserva FOREIGN KEY (id_fecha_reserva)
        REFERENCES dbo.dim_fecha (id_fecha)
);
GO

-- ============================================================================
-- 5. ÍNDICES DE RENDIMIENTO PARA CONSULTAS ANALÍTICAS (BI)
-- ============================================================================
CREATE NONCLUSTERED INDEX IX_fact_aerolinea ON dbo.fact_vuelo_pasaje (id_aerolinea);
CREATE NONCLUSTERED INDEX IX_fact_origen_destino ON dbo.fact_vuelo_pasaje (id_aeropuerto_origen, id_aeropuerto_destino);
CREATE NONCLUSTERED INDEX IX_fact_fecha_salida ON dbo.fact_vuelo_pasaje (id_fecha_salida);
CREATE NONCLUSTERED INDEX IX_fact_canal_pago ON dbo.fact_vuelo_pasaje (id_canal_pago);
CREATE NONCLUSTERED INDEX IX_fact_estado_vuelo ON dbo.fact_vuelo_pasaje (estado_vuelo);
GO

PRINT '>> Script DDL del Modelo Multidimensional ejecutado exitosamente en VuelosDW.';
GO
