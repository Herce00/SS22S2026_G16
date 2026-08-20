from typing import Dict, Tuple
import pandas as pd
import numpy as np

MAPA_AEROLINEAS = {
    'AA': 'American Airlines',
    'AM': 'Aeroméxico',
    'AV': 'Avianca',
    'B6': 'JetBlue',
    'BA': 'British Airways',
    'CM': 'Copa Airlines',
    'DL': 'Delta Air Lines',
    'FR': 'Ryanair',
    'IB': 'Iberia',
    'LA': 'LATAM Airlines',
    'UA': 'United Airlines',
    'WN': 'Southwest Airlines'
}

MAPA_GENEROS = {
    'M': 'M', 'm': 'M', 'Masculino': 'M', 'masculino': 'M',
    'F': 'F', 'f': 'F', 'Femenino': 'F', 'femenino': 'F',
    'X': 'X', 'x': 'X', 'NoBinario': 'X', 'nobinario': 'X'
}


def transformar_datos_vuelos(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    print("[ETL - Transformación] Iniciando limpieza y homologación de datos...")
    df = df_raw.copy()

    df['airline_code'] = df['airline_code'].astype(str).str.strip().str.upper()
    df['airline_name_clean'] = df['airline_code'].map(MAPA_AEROLINEAS).fillna(
        df['airline_name'].astype(str).str.strip().str.title()
    )

    df['passenger_gender_clean'] = df['passenger_gender'].astype(str).str.strip().map(MAPA_GENEROS).fillna('X')

    df['passenger_nationality_clean'] = df['passenger_nationality'].fillna('Desconocida').astype(str).str.strip().str.title()
    df['passenger_nationality_clean'] = df['passenger_nationality_clean'].replace({'Nan': 'Desconocida', '': 'Desconocida'})
    
    mediana_edad = int(df['passenger_age'].median())
    df['passenger_age_clean'] = df['passenger_age'].fillna(mediana_edad).astype(int)

    df['sales_channel_clean'] = df['sales_channel'].fillna('NO_ESPECIFICADO').astype(str).str.strip().str.upper()
    df['sales_channel_clean'] = df['sales_channel_clean'].replace({'NAN': 'NO_ESPECIFICADO', '': 'NO_ESPECIFICADO'})
    
    df['payment_method_clean'] = df['payment_method'].fillna('NO_ESPECIFICADO').astype(str).str.strip().str.upper()
    df['payment_method_clean'] = df['payment_method_clean'].replace({'NAN': 'NO_ESPECIFICADO', '': 'NO_ESPECIFICADO'})

    df['ticket_price_clean'] = df['ticket_price'].astype(str).str.replace(',', '.', regex=False).astype(float).round(2)
    df['ticket_price_usd_est'] = df['ticket_price_usd_est'].astype(float).round(2)
    df['currency'] = df['currency'].astype(str).str.strip().str.upper()

    df['departure_dt'] = pd.to_datetime(df['departure_datetime'], format='mixed')
    df['arrival_dt'] = pd.to_datetime(df['arrival_datetime'], format='mixed')
    df['booking_dt'] = pd.to_datetime(df['booking_datetime'], format='mixed')

    df['aircraft_type'] = df['aircraft_type'].astype(str).str.strip().str.upper()
    df['origin_airport'] = df['origin_airport'].astype(str).str.strip().str.upper()
    df['destination_airport'] = df['destination_airport'].astype(str).str.strip().str.upper()
    df['status'] = df['status'].astype(str).str.strip().str.upper()
    df['cabin_class'] = df['cabin_class'].astype(str).str.strip().str.upper()
    df['flight_number'] = df['flight_number'].astype(str).str.strip().str.upper()

    print("[ETL - Transformación] Construyendo tablas de dimensiones del Esquema Estrella...")

    dim_aerolinea = df[['airline_code', 'airline_name_clean']].drop_duplicates().sort_values('airline_code').reset_index(drop=True)
    dim_aerolinea.columns = ['codigo_aerolinea', 'nombre_aerolinea']
    dim_aerolinea.insert(0, 'id_aerolinea', range(1, len(dim_aerolinea) + 1))

    aeropuertos_unicos = sorted(list(set(df['origin_airport']).union(set(df['destination_airport']))))
    dim_aeropuerto = pd.DataFrame({'codigo_aeropuerto': aeropuertos_unicos})
    dim_aeropuerto.insert(0, 'id_aeropuerto', range(1, len(dim_aeropuerto) + 1))

    dim_pasajero = df[['passenger_id', 'passenger_gender_clean', 'passenger_age_clean', 'passenger_nationality_clean']].drop_duplicates(subset=['passenger_id']).reset_index(drop=True)
    dim_pasajero.columns = ['passenger_id', 'genero', 'edad', 'nacionalidad']
    dim_pasajero.insert(0, 'id_pasajero', range(1, len(dim_pasajero) + 1))

    aeronaves_unicas = sorted(df['aircraft_type'].unique())
    dim_aeronave = pd.DataFrame({'tipo_aeronave': aeronaves_unicas})
    dim_aeronave.insert(0, 'id_aeronave', range(1, len(dim_aeronave) + 1))

    dim_canal_pago = df[['sales_channel_clean', 'payment_method_clean']].drop_duplicates().sort_values(['sales_channel_clean', 'payment_method_clean']).reset_index(drop=True)
    dim_canal_pago.columns = ['canal_venta', 'metodo_pago']
    dim_canal_pago.insert(0, 'id_canal_pago', range(1, len(dim_canal_pago) + 1))

    fechas_todas = pd.concat([df['departure_dt'].dt.date, df['booking_dt'].dt.date]).drop_duplicates().sort_values().reset_index(drop=True)
    dim_fecha = pd.DataFrame({'fecha': pd.to_datetime(fechas_todas)})
    dim_fecha['id_fecha'] = dim_fecha['fecha'].dt.strftime('%Y%m%d').astype(int)
    dim_fecha['anio'] = dim_fecha['fecha'].dt.year
    dim_fecha['trimestre'] = dim_fecha['fecha'].dt.quarter
    dim_fecha['mes'] = dim_fecha['fecha'].dt.month
    dim_fecha['nombre_mes'] = dim_fecha['fecha'].dt.strftime('%B')
    dim_fecha['dia'] = dim_fecha['fecha'].dt.day
    dim_fecha['dia_semana'] = dim_fecha['fecha'].dt.strftime('%A')
    dim_fecha['es_fin_semana'] = dim_fecha['fecha'].dt.dayofweek.isin([5, 6]).astype(int)
    dim_fecha = dim_fecha[['id_fecha', 'fecha', 'anio', 'trimestre', 'mes', 'nombre_mes', 'dia', 'dia_semana', 'es_fin_semana']]

    print("[ETL - Transformación] Generando tabla de hechos 'fact_vuelo_pasaje' con claves foráneas...")

    df['id_fecha_salida'] = df['departure_dt'].dt.strftime('%Y%m%d').astype(int)
    df['id_fecha_reserva'] = df['booking_dt'].dt.strftime('%Y%m%d').astype(int)

    df_fact = df.merge(dim_aerolinea, left_on=['airline_code', 'airline_name_clean'], right_on=['codigo_aerolinea', 'nombre_aerolinea'], how='left')
    df_fact = df_fact.merge(dim_aeropuerto.rename(columns={'id_aeropuerto': 'id_aeropuerto_origen'}), left_on='origin_airport', right_on='codigo_aeropuerto', how='left')
    df_fact = df_fact.merge(dim_aeropuerto.rename(columns={'id_aeropuerto': 'id_aeropuerto_destino'}), left_on='destination_airport', right_on='codigo_aeropuerto', how='left')
    df_fact = df_fact.merge(dim_pasajero[['id_pasajero', 'passenger_id']], on='passenger_id', how='left')
    df_fact = df_fact.merge(dim_aeronave, left_on='aircraft_type', right_on='tipo_aeronave', how='left')
    df_fact = df_fact.merge(dim_canal_pago, left_on=['sales_channel_clean', 'payment_method_clean'], right_on=['canal_venta', 'metodo_pago'], how='left')

    fact_vuelo_pasaje = pd.DataFrame({
        'id_fact': range(1, len(df_fact) + 1),
        'record_id': df_fact['record_id'].astype(int),
        'flight_number': df_fact['flight_number'],
        'id_aerolinea': df_fact['id_aerolinea'].astype(int),
        'id_aeropuerto_origen': df_fact['id_aeropuerto_origen'].astype(int),
        'id_aeropuerto_destino': df_fact['id_aeropuerto_destino'].astype(int),
        'id_pasajero': df_fact['id_pasajero'].astype(int),
        'id_aeronave': df_fact['id_aeronave'].astype(int),
        'id_canal_pago': df_fact['id_canal_pago'].astype(int),
        'id_fecha_salida': df_fact['id_fecha_salida'].astype(int),
        'id_fecha_reserva': df_fact['id_fecha_reserva'].astype(int),
        'estado_vuelo': df_fact['status'],
        'clase_cabina': df_fact['cabin_class'],
        'asiento': df_fact['seat'].astype(str).str.strip().replace({'nan': None, 'None': None, '': None}),
        'fecha_salida': df_fact['departure_dt'],
        'fecha_llegada': df_fact['arrival_dt'],
        'duracion_min': df_fact['duration_min'],
        'demora_min': df_fact['delay_min'],
        'precio_boleto_original': df_fact['ticket_price_clean'],
        'moneda_original': df_fact['currency'],
        'precio_boleto_usd': df_fact['ticket_price_usd_est'],
        'total_maletas': df_fact['bags_total'].astype(int),
        'maletas_facturadas': df_fact['bags_checked'].astype(int)
    })

    assert len(fact_vuelo_pasaje) == len(df_raw), "Error de integridad: el número de filas en la tabla de hechos no coincide con el origen."
    assert fact_vuelo_pasaje[['id_aerolinea', 'id_aeropuerto_origen', 'id_aeropuerto_destino', 'id_pasajero', 'id_aeronave', 'id_canal_pago']].isnull().sum().sum() == 0, "Error: Existen claves foráneas nulas en la tabla de hechos."

    tablas_dimensionales = {
        'dim_fecha': dim_fecha,
        'dim_aerolinea': dim_aerolinea,
        'dim_aeropuerto': dim_aeropuerto,
        'dim_pasajero': dim_pasajero,
        'dim_aeronave': dim_aeronave,
        'dim_canal_pago': dim_canal_pago,
        'fact_vuelo_pasaje': fact_vuelo_pasaje
    }

    print("[ETL - Transformación] Éxito: Esquema Estrella generado completamente sin claves foráneas huérfanas.")
    return df, tablas_dimensionales
