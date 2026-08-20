-- ============================================================================
-- CONSULTAS SQL ANALÍTICAS DE VALIDACIÓN Y BUSINESS INTELLIGENCE
-- Base de Datos: VuelosDW (Microsoft SQL Server)
-- Curso: Seminario de Sistemas 2 - 2do Semestre 2026 - Grupo 16
-- Integrantes:
--   - César Rolando Hernández Palacios (202000806)
--   - Keneth Willard Lopez Ovalle (202100106)
-- ============================================================================

USE VuelosDW;
GO

-- ============================================================================
-- CONSULTA 1: VOLUMEN Y PROPORCIÓN DE VUELOS POR ESTADO
-- Objetivo: Evaluar la completitud operativa del dataset, desglosando el total
-- de transacciones, porcentaje de participación, ingreso total y demoras promedio.
-- ============================================================================
PRINT '=== CONSULTA 1: Volumen y Proporción de Vuelos por Estado ===';
SELECT 
    f.estado_vuelo AS [Estado de Vuelo],
    COUNT(f.id_fact) AS [Total Vuelos/Pasajes],
    CAST(COUNT(f.id_fact) * 100.0 / (SELECT COUNT(*) FROM dbo.fact_vuelo_pasaje) AS DECIMAL(5, 2)) AS [Porcentaje (%)],
    SUM(f.precio_boleto_usd) AS [Ingreso Total (USD)],
    AVG(f.precio_boleto_usd) AS [Ticket Promedio (USD)],
    AVG(ISNULL(f.demora_min, 0)) AS [Demora Promedio (min)]
FROM dbo.fact_vuelo_pasaje f
GROUP BY f.estado_vuelo
ORDER BY [Total Vuelos/Pasajes] DESC;
GO

-- ============================================================================
-- CONSULTA 2: TOP 5 AEROLÍNEAS CON MAYOR VOLUMEN E INGRESOS EN USD
-- Objetivo: Identificar los socios comerciales estratégicos según volumen
-- de pasajeros transportados y facturación bruta acumulada.
-- ============================================================================
PRINT '=== CONSULTA 2: Top 5 Aerolíneas por Ingresos y Pasajeros ===';
SELECT TOP 5
    a.codigo_aerolinea AS [Código],
    a.nombre_aerolinea AS [Aerolínea],
    COUNT(f.id_fact) AS [Pasajeros Transportados],
    SUM(f.precio_boleto_usd) AS [Facturación Total (USD)],
    AVG(f.precio_boleto_usd) AS [Tarifa Promedio (USD)],
    SUM(f.total_maletas) AS [Total Equipaje Procesado]
FROM dbo.fact_vuelo_pasaje f
INNER JOIN dbo.dim_aerolinea a ON f.id_aerolinea = a.id_aerolinea
GROUP BY a.codigo_aerolinea, a.nombre_aerolinea
ORDER BY [Facturación Total (USD)] DESC;
GO

-- ============================================================================
-- CONSULTA 3: TOP 5 RUTAS MÁS TRANSITADAS (ORIGEN - DESTINO)
-- Objetivo: Mapear los corredores aéreos de mayor demanda para optimización
-- de flotas y asignación de frecuencias de vuelo.
-- ============================================================================
PRINT '=== CONSULTA 3: Top 5 Rutas Más Transitadas (Origen - Destino) ===';
SELECT TOP 5
    ao.codigo_aeropuerto AS [Aeropuerto Origen],
    ad.codigo_aeropuerto AS [Aeropuerto Destino],
    ao.codigo_aeropuerto + ' -> ' + ad.codigo_aeropuerto AS [Ruta Comercial],
    COUNT(f.id_fact) AS [Frecuencia de Pasajeros],
    SUM(f.precio_boleto_usd) AS [Ingreso Generado (USD)],
    AVG(ISNULL(f.duracion_min, 0)) AS [Duración Promedio (min)]
FROM dbo.fact_vuelo_pasaje f
INNER JOIN dbo.dim_aeropuerto ao ON f.id_aeropuerto_origen = ao.id_aeropuerto
INNER JOIN dbo.dim_aeropuerto ad ON f.id_aeropuerto_destino = ad.id_aeropuerto
GROUP BY ao.codigo_aeropuerto, ad.codigo_aeropuerto
ORDER BY [Frecuencia de Pasajeros] DESC;
GO

-- ============================================================================
-- CONSULTA 4: DISTRIBUCIÓN DEMOGRÁFICA DE PASAJEROS (GÉNERO, EDAD Y NACIONALIDAD)
-- Objetivo: Segmentación analítica de la base de clientes para campañas de marketing.
-- ============================================================================
PRINT '=== CONSULTA 4A: Distribución por Género ===';
SELECT 
    p.genero AS [Género Canónico],
    COUNT(f.id_fact) AS [Total Pasajeros],
    CAST(COUNT(f.id_fact) * 100.0 / (SELECT COUNT(*) FROM dbo.fact_vuelo_pasaje) AS DECIMAL(5, 2)) AS [Proporción (%)],
    SUM(f.precio_boleto_usd) AS [Gasto Total (USD)],
    AVG(p.edad) AS [Edad Promedio]
FROM dbo.fact_vuelo_pasaje f
INNER JOIN dbo.dim_pasajero p ON f.id_pasajero = p.id_pasajero
GROUP BY p.genero
ORDER BY [Total Pasajeros] DESC;
GO

PRINT '=== CONSULTA 4B: Distribución por Rango de Edad ===';
SELECT 
    CASE 
        WHEN p.edad < 25 THEN '1. Menores de 25 años'
        WHEN p.edad BETWEEN 25 AND 40 THEN '2. Adultos Jóvenes (25-40)'
        WHEN p.edad BETWEEN 41 AND 60 THEN '3. Adultos Maduros (41-60)'
        ELSE '4. Adultos Mayores (>60)'
    END AS [Rango de Edad],
    COUNT(f.id_fact) AS [Total Pasajeros],
    AVG(f.precio_boleto_usd) AS [Gasto Promedio (USD)],
    SUM(f.precio_boleto_usd) AS [Gasto Acumulado (USD)]
FROM dbo.fact_vuelo_pasaje f
INNER JOIN dbo.dim_pasajero p ON f.id_pasajero = p.id_pasajero
GROUP BY 
    CASE 
        WHEN p.edad < 25 THEN '1. Menores de 25 años'
        WHEN p.edad BETWEEN 25 AND 40 THEN '2. Adultos Jóvenes (25-40)'
        WHEN p.edad BETWEEN 41 AND 60 THEN '3. Adultos Maduros (41-60)'
        ELSE '4. Adultos Mayores (>60)'
    END
ORDER BY [Rango de Edad];
GO

PRINT '=== CONSULTA 4C: Top 5 Nacionalidades con Mayor Volumen ===';
SELECT TOP 5
    p.nacionalidad AS [Nacionalidad],
    COUNT(f.id_fact) AS [Pasajeros Registrados],
    SUM(f.precio_boleto_usd) AS [Ingreso Total (USD)]
FROM dbo.fact_vuelo_pasaje f
INNER JOIN dbo.dim_pasajero p ON f.id_pasajero = p.id_pasajero
GROUP BY p.nacionalidad
ORDER BY [Pasajeros Registrados] DESC;
GO

-- ============================================================================
-- CONSULTA 5: ANÁLISIS DE DEMORAS OPERATIVAS POR AEROLÍNEA Y ORIGEN
-- Objetivo: Medir la eficiencia y puntualidad operativa por aerolínea.
-- ============================================================================
PRINT '=== CONSULTA 5: Puntualidad y Demoras por Aerolínea ===';
SELECT 
    a.nombre_aerolinea AS [Aerolínea],
    COUNT(f.id_fact) AS [Total Vuelos Operados],
    SUM(CASE WHEN f.demora_min > 0 THEN 1 ELSE 0 END) AS [Vuelos Demorados],
    CAST(SUM(CASE WHEN f.demora_min > 0 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(f.id_fact) AS DECIMAL(5, 2)) AS [Tasa de Demora (%)],
    AVG(CASE WHEN f.demora_min > 0 THEN f.demora_min ELSE NULL END) AS [Demora Promedio en Retrasos (min)],
    SUM(CASE WHEN f.estado_vuelo = 'CANCELLED' THEN 1 ELSE 0 END) AS [Vuelos Cancelados]
FROM dbo.fact_vuelo_pasaje f
INNER JOIN dbo.dim_aerolinea a ON f.id_aerolinea = a.id_aerolinea
GROUP BY a.nombre_aerolinea
ORDER BY [Tasa de Demora (%)] DESC;
GO

-- ============================================================================
-- CONSULTA 6: RENDIMIENTO COMERCIAL POR CANAL DE VENTA Y MÉTODO DE PAGO
-- Objetivo: Identificar los canales comerciales y pasarelas de pago más rentables.
-- ============================================================================
PRINT '=== CONSULTA 6: Ingresos por Canal de Venta y Método de Pago ===';
SELECT 
    cp.canal_venta AS [Canal de Venta],
    cp.metodo_pago AS [Método de Pago],
    COUNT(f.id_fact) AS [Boletos Vendidos],
    SUM(f.precio_boleto_usd) AS [Ingreso Total (USD)],
    AVG(f.precio_boleto_usd) AS [Ticket Promedio (USD)],
    CAST(SUM(f.precio_boleto_usd) * 100.0 / (SELECT SUM(precio_boleto_usd) FROM dbo.fact_vuelo_pasaje) AS DECIMAL(5, 2)) AS [Participación Ventas (%)]
FROM dbo.fact_vuelo_pasaje f
INNER JOIN dbo.dim_canal_pago cp ON f.id_canal_pago = cp.id_canal_pago
GROUP BY cp.canal_venta, cp.metodo_pago
ORDER BY [Ingreso Total (USD)] DESC;
GO
