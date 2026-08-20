import os
import pandas as pd


def extraer_datos_vuelos(ruta_archivo: str = "dataset_vuelos_crudo.csv") -> pd.DataFrame:
    if not os.path.isabs(ruta_archivo):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        posible_ruta = os.path.join(base_dir, ruta_archivo)
        if os.path.exists(posible_ruta):
            ruta_archivo = posible_ruta

    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"Error ETL [Extracción]: No se encontró el archivo de datos en: {ruta_archivo}")

    print(f"[ETL - Extracción] Cargando datos crudos desde: {ruta_archivo}")
    df_raw = pd.read_csv(ruta_archivo)

    if df_raw.empty:
        raise ValueError("Error ETL [Extracción]: El archivo CSV de origen está vacío.")

    print(f"[ETL - Extracción] Éxito: {len(df_raw):,} registros y {len(df_raw.columns)} columnas extraídas correctamente.")
    return df_raw
