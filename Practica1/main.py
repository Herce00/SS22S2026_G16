import os
import argparse
from etl.extract import extraer_datos_vuelos
from etl.transform import transformar_datos_vuelos
from etl.load import crear_motor_sql_server, cargar_modelo_multidimensional, cargar_a_sqlite_local


def parse_argumentos():
    parser = argparse.ArgumentParser(description="Pipeline ETL de Vuelos para Modelo Multidimensional")
    parser.add_argument(
        "--archivo-crudo",
        type=str,
        default="dataset_vuelos_crudo.csv",
        help="Ruta al archivo CSV con los datos crudos de vuelos"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Ejecuta la carga únicamente en base de datos SQLite local para pruebas"
    )
    parser.add_argument(
        "--export-staging",
        action="store_true",
        default=True,
        help="Exporta DataFrames limpios a formato Parquet/CSV en staging"
    )
    return parser.parse_args()


def main():
    args = parse_argumentos()

    print("=" * 80)
    print("INICIANDO PIPELINE ETL: VUELOS DATA WAREHOUSE (PRACTICA 1 - GRUPO 16)")
    print("=" * 80)

    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(ruta_base, args.archivo_crudo)
    df_raw = extraer_datos_vuelos(ruta_csv)

    df_limpio, tablas_dimensionales = transformar_datos_vuelos(df_raw)

    if args.export_staging:
        staging_dir = os.path.join(ruta_base, "staging")
        os.makedirs(staging_dir, exist_ok=True)
        print(f"[ETL - Staging] Exportando tablas dimensionales a: {staging_dir}")
        for nombre, df_tab in tablas_dimensionales.items():
            df_tab.to_parquet(os.path.join(staging_dir, f"{nombre}.parquet"), index=False)
        print("[ETL - Staging] [OK] Tablas Parquet exportadas correctamente.")

    if args.local:
        print("\n[ETL - Modo Local Solicitado] Realizando carga en SQLite local...")
        ruta_sqlite = os.path.join(ruta_base, "vuelos_local.db")
        cargar_a_sqlite_local(ruta_sqlite, tablas_dimensionales)
        print("\n[OK] Pipeline ETL finalizado exitosamente en modo Local (SQLite).")
        return

    print("\n[ETL - Carga SQL Server] Intentando conexion a Microsoft SQL Server...")
    try:
        engine_sql = crear_motor_sql_server()
        with engine_sql.connect() as conn:
            print("[ETL - Carga SQL Server] [OK] Conexion establecida con exito con SQL Server.")
        
        cargar_modelo_multidimensional(engine_sql, tablas_dimensionales, if_exists="append")
        print("\n" + "=" * 80)
        print("[OK] PIPELINE ETL COMPLETADO EXITOSAMENTE EN MICROSOFT SQL SERVER")
        print("=" * 80)

    except Exception as e:
        print("\n" + "!" * 80)
        print(f"[AVISO - Carga SQL Server] No se pudo conectar a la instancia de SQL Server:")
        print(f">> Detalle: {e}")
        print("\n>> Ejecutando carga automatica de respaldo en SQLite local (vuelos_local.db)...")
        print("!" * 80)
        
        ruta_sqlite = os.path.join(ruta_base, "vuelos_local.db")
        cargar_a_sqlite_local(ruta_sqlite, tablas_dimensionales)
        
        print("\n" + "=" * 80)
        print("[OK] DATOS PROCESADOS Y DISPONIBLES LOCALMENTE EN 'vuelos_local.db'")
        print(">> Nota para Persona B: Ejecutar 'schema.sql' en SQL Server y correr nuevamente:")
        print(">>   python main.py")
        print("=" * 80)


if __name__ == "__main__":
    main()
