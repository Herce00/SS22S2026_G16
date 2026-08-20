import os
import pandas as pd
from etl.extract import extraer_datos_vuelos
from etl.transform import transformar_datos_vuelos
from etl.load import cargar_a_sqlite_local


def ejecutar_validacion_local():
    print("=" * 80)
    print("INICIANDO SUITE DE VALIDACIÓN LOCAL DE ETL Y MODELO MULTIDIMENSIONAL")
    print("=" * 80)

    ruta_csv = os.path.join(os.path.dirname(__file__), "dataset_vuelos_crudo.csv")
    df_raw = extraer_datos_vuelos(ruta_csv)
    assert len(df_raw) == 10000, f"Error en extracción: se esperaban 10000 registros, obtenidos {len(df_raw)}"

    df_limpio, tablas_dimensionales = transformar_datos_vuelos(df_raw)

    print("\n--- Verificación de Integridad de Datos Transformados ---")
    assert len(tablas_dimensionales['dim_aerolinea']) == 12, "Fallo: dim_aerolinea debe tener 12 aerolíneas"
    assert len(tablas_dimensionales['dim_aeropuerto']) == 15, "Fallo: dim_aeropuerto debe tener 15 aeropuertos"
    assert len(tablas_dimensionales['dim_aeronave']) == 12, "Fallo: dim_aeronave debe tener 12 modelos"
    assert len(tablas_dimensionales['dim_canal_pago']) == 30, "Fallo: dim_canal_pago debe tener 30 combinaciones"
    assert len(tablas_dimensionales['fact_vuelo_pasaje']) == 10000, "Fallo: fact_vuelo_pasaje debe tener 10,000 registros"

    fact = tablas_dimensionales['fact_vuelo_pasaje']
    assert fact[['id_aerolinea', 'id_aeropuerto_origen', 'id_aeropuerto_destino', 'id_pasajero', 'id_aeronave', 'id_canal_pago', 'id_fecha_salida', 'id_fecha_reserva']].isnull().sum().sum() == 0, "Fallo: existen FKs nulas en fact table"
    assert (fact['estado_vuelo'] == 'CANCELLED').sum() == 560, "Fallo: se esperaban exactamente 560 vuelos cancelados"
    print("[OK] Todas las aserciones de DataFrames superadas con exito.")

    ruta_db = os.path.join(os.path.dirname(__file__), "vuelos_local.db")
    engine = cargar_a_sqlite_local(ruta_db, tablas_dimensionales)

    print("\n" + "=" * 80)
    print("EJECUTANDO LAS 6 CONSULTAS ANALÍTICAS DE NEGOCIO SOBRE LA BASE DE DATOS LOCAL")
    print("=" * 80)

    q1 = """
    SELECT 
        f.estado_vuelo AS estado,
        COUNT(f.id_fact) AS total_vuelos,
        ROUND(COUNT(f.id_fact) * 100.0 / 10000.0, 2) AS porcentaje,
        ROUND(SUM(f.precio_boleto_usd), 2) AS ingreso_total_usd,
        ROUND(AVG(f.precio_boleto_usd), 2) AS ticket_promedio_usd,
        ROUND(AVG(COALESCE(f.demora_min, 0)), 2) AS demora_promedio_min
    FROM fact_vuelo_pasaje f
    GROUP BY f.estado_vuelo
    ORDER BY total_vuelos DESC;
    """
    df_q1 = pd.read_sql_query(q1, engine)
    print("\n>>> CONSULTA 1: Volumen y Proporción de Vuelos por Estado")
    print(df_q1.to_string(index=False))

    q2 = """
    SELECT 
        a.codigo_aerolinea AS codigo,
        a.nombre_aerolinea AS aerolinea,
        COUNT(f.id_fact) AS pasajeros_transportados,
        ROUND(SUM(f.precio_boleto_usd), 2) AS facturacion_total_usd,
        ROUND(AVG(f.precio_boleto_usd), 2) AS tarifa_promedio_usd,
        SUM(f.total_maletas) AS total_equipaje
    FROM fact_vuelo_pasaje f
    JOIN dim_aerolinea a ON f.id_aerolinea = a.id_aerolinea
    GROUP BY a.codigo_aerolinea, a.nombre_aerolinea
    ORDER BY facturacion_total_usd DESC
    LIMIT 5;
    """
    df_q2 = pd.read_sql_query(q2, engine)
    print("\n>>> CONSULTA 2: Top 5 Aerolíneas por Ingresos y Pasajeros")
    print(df_q2.to_string(index=False))

    q3 = """
    SELECT 
        ao.codigo_aeropuerto || ' -> ' || ad.codigo_aeropuerto AS ruta_comercial,
        COUNT(f.id_fact) AS frecuencia_pasajeros,
        ROUND(SUM(f.precio_boleto_usd), 2) AS ingreso_generado_usd,
        ROUND(AVG(COALESCE(f.duracion_min, 0)), 2) AS duracion_promedio_min
    FROM fact_vuelo_pasaje f
    JOIN dim_aeropuerto ao ON f.id_aeropuerto_origen = ao.id_aeropuerto
    JOIN dim_aeropuerto ad ON f.id_aeropuerto_destino = ad.id_aeropuerto
    GROUP BY ao.codigo_aeropuerto, ad.codigo_aeropuerto
    ORDER BY frecuencia_pasajeros DESC
    LIMIT 5;
    """
    df_q3 = pd.read_sql_query(q3, engine)
    print("\n>>> CONSULTA 3: Top 5 Rutas Más Transitadas (Origen -> Destino)")
    print(df_q3.to_string(index=False))

    q4a = """
    SELECT 
        p.genero AS genero,
        COUNT(f.id_fact) AS total_pasajeros,
        ROUND(COUNT(f.id_fact) * 100.0 / 10000.0, 2) AS proporcion_pct,
        ROUND(SUM(f.precio_boleto_usd), 2) AS gasto_total_usd,
        ROUND(AVG(p.edad), 1) AS edad_promedio
    FROM fact_vuelo_pasaje f
    JOIN dim_pasajero p ON f.id_pasajero = p.id_pasajero
    GROUP BY p.genero
    ORDER BY total_pasajeros DESC;
    """
    df_q4a = pd.read_sql_query(q4a, engine)
    print("\n>>> CONSULTA 4A: Distribución Demográfica por Género")
    print(df_q4a.to_string(index=False))

    q4b = """
    SELECT 
        CASE 
            WHEN p.edad < 25 THEN '1. Menores de 25 años'
            WHEN p.edad BETWEEN 25 AND 40 THEN '2. Adultos Jóvenes (25-40)'
            WHEN p.edad BETWEEN 41 AND 60 THEN '3. Adultos Maduros (41-60)'
            ELSE '4. Adultos Mayores (>60)'
        END AS rango_edad,
        COUNT(f.id_fact) AS total_pasajeros,
        ROUND(AVG(f.precio_boleto_usd), 2) AS gasto_promedio_usd,
        ROUND(SUM(f.precio_boleto_usd), 2) AS gasto_acumulado_usd
    FROM fact_vuelo_pasaje f
    JOIN dim_pasajero p ON f.id_pasajero = p.id_pasajero
    GROUP BY rango_edad
    ORDER BY rango_edad;
    """
    df_q4b = pd.read_sql_query(q4b, engine)
    print("\n>>> CONSULTA 4B: Distribución por Rango de Edad")
    print(df_q4b.to_string(index=False))

    q5 = """
    SELECT 
        a.nombre_aerolinea AS aerolinea,
        COUNT(f.id_fact) AS total_vuelos,
        SUM(CASE WHEN f.demora_min > 0 THEN 1 ELSE 0 END) AS vuelos_demorados,
        ROUND(SUM(CASE WHEN f.demora_min > 0 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(f.id_fact), 2) AS tasa_demora_pct,
        ROUND(AVG(CASE WHEN f.demora_min > 0 THEN f.demora_min ELSE NULL END), 2) AS demora_promedio_min,
        SUM(CASE WHEN f.estado_vuelo = 'CANCELLED' THEN 1 ELSE 0 END) AS vuelos_cancelados
    FROM fact_vuelo_pasaje f
    JOIN dim_aerolinea a ON f.id_aerolinea = a.id_aerolinea
    GROUP BY a.nombre_aerolinea
    ORDER BY tasa_demora_pct DESC;
    """
    df_q5 = pd.read_sql_query(q5, engine)
    print("\n>>> CONSULTA 5: Puntualidad y Demoras Operativas por Aerolínea")
    print(df_q5.to_string(index=False))

    q6 = """
    SELECT 
        cp.canal_venta AS canal_venta,
        cp.metodo_pago AS metodo_pago,
        COUNT(f.id_fact) AS boletos_vendidos,
        ROUND(SUM(f.precio_boleto_usd), 2) AS ingreso_total_usd,
        ROUND(AVG(f.precio_boleto_usd), 2) AS ticket_promedio_usd
    FROM fact_vuelo_pasaje f
    JOIN dim_canal_pago cp ON f.id_canal_pago = cp.id_canal_pago
    GROUP BY cp.canal_venta, cp.metodo_pago
    ORDER BY ingreso_total_usd DESC
    LIMIT 10;
    """
    df_q6 = pd.read_sql_query(q6, engine)
    print("\n>>> CONSULTA 6: Top 10 Canales y Métodos de Pago por Facturación")
    print(df_q6.to_string(index=False))

    print("\n" + "=" * 80)
    print("VALIDACION LOCAL COMPLETADA EXITOSAMENTE! (100% de tests y consultas superados)")
    print("=" * 80)


if __name__ == "__main__":
    ejecutar_validacion_local()
