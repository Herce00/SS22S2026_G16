import os
import platform

from typing import Dict, Optional
import pandas as pd
from sqlalchemy import create_engine, Engine
from dotenv import load_dotenv

load_dotenv()


def crear_motor_sql_server(
    servidor: Optional[str] = None,
    puerto: Optional[str] = None,
    base_datos: Optional[str] = None,
    usuario: Optional[str] = None,
    password: Optional[str] = None,
) -> Engine:
    servidor = servidor or os.getenv("SQL_SERVER_HOST", "localhost")
    puerto = puerto or os.getenv("SQL_SERVER_PORT", "1433")
    base_datos = base_datos or os.getenv("SQL_SERVER_DATABASE", "VuelosDW")
    usuario = usuario or os.getenv("SQL_SERVER_USER", "")
    password = password or os.getenv("SQL_SERVER_PASSWORD", "")

    sistema = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'

    if sistema == "Windows":
        url_conexion = (
            f"mssql+pyodbc://{usuario}:{password}@{servidor}:{puerto}/{base_datos}"
            f"?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=yes"
        )
    else:
        # macOS y Linux siguen usando pymssql con formato de coma
        url_conexion = f"mssql+pymssql://{usuario}:{password}@{servidor}:{puerto}/{base_datos}"

    print(
        f"[ETL - Carga] Sistema detectado: {sistema}. Configurando motor de conexión: servidor='{servidor}', puerto='{puerto}', base_datos='{base_datos}'")
    engine = create_engine(url_conexion)
    return engine


def cargar_modelo_multidimensional(
    engine: Engine,
    tablas_dimensionales: Dict[str, pd.DataFrame],
    if_exists: str = "append",
    chunksize: int = 1000
) -> Dict[str, int]:
    orden_carga = [
        'dim_fecha',
        'dim_aerolinea',
        'dim_aeropuerto',
        'dim_pasajero',
        'dim_aeronave',
        'dim_canal_pago',
        'fact_vuelo_pasaje'
    ]

    resumen_carga = {}

    print(
        f"[ETL - Carga] Iniciando carga masiva de datos en {engine.dialect.name.upper()}...")

    with engine.begin() as conn:
        for nombre_tabla in orden_carga:
            if nombre_tabla in tablas_dimensionales:
                df_tabla = tablas_dimensionales[nombre_tabla]
                print(
                    f"[ETL - Carga] Insertando {len(df_tabla):,} filas en la tabla '{nombre_tabla}'...")

                df_tabla.to_sql(
                    name=nombre_tabla,
                    con=conn,
                    if_exists=if_exists,
                    index=False,
                    chunksize=chunksize,
                    method='multi' if engine.dialect.name == 'sqlite' else None
                )
                resumen_carga[nombre_tabla] = len(df_tabla)
                print(
                    f"[ETL - Carga] [OK] '{nombre_tabla}' cargada exitosamente.")

    print(
        f"[ETL - Carga] Exito: Todas las tablas ({len(resumen_carga)}) fueron cargadas correctamente.")
    return resumen_carga


def cargar_a_sqlite_local(
    ruta_sqlite: str,
    tablas_dimensionales: Dict[str, pd.DataFrame]
) -> Engine:
    print(
        f"[ETL - Local] Creando base de datos SQLite de validación en: {ruta_sqlite}")
    engine_sqlite = create_engine(f"sqlite:///{ruta_sqlite}")
    cargar_modelo_multidimensional(
        engine_sqlite, tablas_dimensionales, if_exists="replace")
    return engine_sqlite
