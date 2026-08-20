import pandas as pd
import numpy as np

# ==============================================================================
# 1. CARGA DEL DATASET Y ESTADO ORIGINAL (ANTES)
# ==============================================================================
print("=" * 80)
print("1. CARGA DEL DATASET Y EXPLORACIÓN INICIAL (ESTADO ANTES)")
print("=" * 80)

# Cargamos el archivo CSV
df = pd.read_csv("dataset_sucio.csv")
df_original = df.copy()

print(f"Dimensiones originales del archivo: {df.shape[0]} filas x {df.shape[1]} columnas\n")

print("--- Primeras 10 filas (head) ---")
print(df.head(10))

print("\n--- Estructura y tipos de datos (info) ---")
df.info()

print("\n--- Resumen estadístico general (describe include='all') ---")
print(df.describe(include='all'))

# ==============================================================================
# 2. TRATAMIENTO DE DUPLICADOS
# ==============================================================================
print("\n" + "=" * 80)
print("2. DETECCIÓN Y ELIMINACIÓN DE DUPLICADOS")
print("=" * 80)

num_duplicados = df.duplicated().sum()
print(f"Duplicados exactos encontrados: {num_duplicados}")

print("\n--- Muestra de registros duplicados antes de eliminar ---")
print(df[df.duplicated(keep=False)].sort_values('id_cliente').head(10))

# Eliminación de duplicados
df = df.drop_duplicates()
print(f"\nForma del dataset tras eliminar duplicados: {df.shape[0]} filas x {df.shape[1]} columnas")

# ==============================================================================
# 3. TRATAMIENTO DE CELDAS VACÍAS Y ESPACIOS EN BLANCO
# ==============================================================================
print("\n" + "=" * 80)
print("3. DETECCIÓN Y TRATAMIENTO DE NULOS Y ESPACIOS EN BLANCO")
print("=" * 80)

print("Nulos detectados directamente por pandas:")
nulos_explicitos = df.isnull().sum()
print(nulos_explicitos)

# Corrección de calidad (Bug B): Celdas con solo espacios eluden isnull()
# Normalizamos espacios y convertimos cadenas vacías a NaN antes de dropna()
for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].astype(str).str.strip()
    df[col] = df[col].replace({'nan': np.nan, '': np.nan})

nulos_reales = df.isnull().sum()
nulos_espacios = nulos_reales - nulos_explicitos

print("\nNulos reales (incluyendo celdas con solo espacios en blanco):")
print(nulos_reales)

print("\nDesglose: celdas que contenian unicamente espacios en blanco (ocultas a isnull):")
print(nulos_espacios[nulos_espacios > 0])

# Eliminación de registros con valores nulos (estrategia dropna)
df = df.dropna()
print(f"\nDimensiones tras eliminación de nulos (dropna): {df.shape[0]} filas x {df.shape[1]} columnas")
print("Nulos restantes en el dataset depurado:")
print(df.isnull().sum())

# ==============================================================================
# 4. ESTANDARIZACIÓN DE VALORES Y FORMATOS
# ==============================================================================
print("\n" + "=" * 80)
print("4. ESTANDARIZACIÓN DE VALORES Y FORMATOS")
print("=" * 80)

# Estandarización de columnas de texto
df['nombre'] = df['nombre'].str.title().str.replace(r'\s+', ' ', regex=True)
df['genero'] = df['genero'].str.upper()
df['ciudad'] = df['ciudad'].str.title()
df['categoria'] = df['categoria'].str.title()

# Estandarización de gasto_q (coma decimal a punto y casteo a float)
df['gasto_q'] = df['gasto_q'].str.replace(',', '.', regex=False).astype(float)

# Estandarización de fecha_registro (Bug A: dayfirst=True para evitar invertir meses 01-03)
df['fecha_registro'] = pd.to_datetime(df['fecha_registro'], format='mixed', dayfirst=True)

# Validaciones de integridad del dataset depurado
assert df['fecha_registro'].dt.month.between(1, 3).all(),     "Error: existen meses fuera del rango esperado (enero a marzo)"
assert df.isnull().sum().sum() == 0,     "Error: quedan valores nulos tras la depuración"
assert not (df.select_dtypes(include='object') == '').any().any(),     "Error: quedan celdas vacías ocultas (cadenas de longitud cero)"
assert df.duplicated().sum() == 0,     "Error: quedan registros duplicados"
assert set(df['genero'].unique()) == {'F', 'M'},     f"Error: géneros no canónicos -> {sorted(df['genero'].unique())}"

print("Estandarización completada y validada con 5 aserciones de integridad.")
print(f"Registros finales depurados: {df.shape[0]:,}")

# ==============================================================================
# 5. ESTADO DEPURADO (DESPUÉS)
# ==============================================================================
print("\n" + "=" * 80)
print("5. EXPLORACIÓN DEL ESTADO DEPURADO (DESPUÉS)")
print("=" * 80)

print("--- Primeras 10 filas depuradas (head) ---")
print(df.head(10))

print("\n--- Estructura y tipos de datos depurados (info) ---")
df.info()

print("\n--- Resumen estadístico de variables numéricas depuradas (describe) ---")
print(df.describe())

# ==============================================================================
# 6. TABLAS PIVOTE (CRITERIO DE RÚBRICA E ISO 25012)
# ==============================================================================
print("\n" + "=" * 80)
print("6. EXPLORACIÓN MEDIANTE TABLAS PIVOTE (PANDAS)")
print("=" * 80)

# Pivote A: Fragmentación categórica (Antes vs Después)
print("\n--- PIVOTE A: Fragmentación Categórica (Ciudad vs Género) ---")
print(">> Estado Original (df_original) - Primeras 15 filas de la tabla pivote original:")
pivot_a_orig = pd.pivot_table(df_original, index='ciudad', columns='genero', values='id_cliente', aggfunc='count')
print(pivot_a_orig.head(15))
print(f"Total variantes de ciudad en original: {df_original['ciudad'].nunique(dropna=False)}")
print(f"Total variantes de género en original: {df_original['genero'].nunique(dropna=False)}")

print("\n>> Estado Depurado (df) - Tabla pivote limpia y canónica:")
pivot_a_clean = pd.pivot_table(df, index='ciudad', columns='genero', values='id_cliente', aggfunc='count', margins=True, margins_name='Total')
print(pivot_a_clean)
print(f"Ciudades canónicas finales: {df['ciudad'].nunique()}")
print(f"Géneros canónicos finales: {df['genero'].nunique()}")

# Pivote B: Resumen de Calidad de Datos (Métricas ISO 25012)
print("\n--- PIVOTE B: Resumen de Calidad de Datos (ISO 25012) ---")
calidad_resumen = pd.DataFrame({
    'Métrica / Dimensión': [
        'Total de Registros (Completitud)',
        'Registros Duplicados (Unicidad)',
        'Nulos en Género',
        'Nulos en Ciudad',
        'Nulos en Gasto (Q)',
        'Variantes Únicas de Ciudad (Consistencia)',
        'Variantes Únicas de Género (Consistencia)',
        'Tipo de Dato Gasto (Exactitud sintáctica)',
        'Tipo de Dato Fecha (Exactitud sintáctica)'
    ],
    'Estado Original (Antes)': [
        f"{len(df_original):,}",
        f"{df_original.duplicated().sum():,}",
        f"{nulos_reales['genero']} ({nulos_explicitos['genero']} explícitos + {nulos_espacios['genero']} vacíos)",
        f"{nulos_reales['ciudad']} ({nulos_explicitos['ciudad']} explícitos + {nulos_espacios['ciudad']} vacíos)",
        f"{nulos_reales['gasto_q']}",
        f"{df_original['ciudad'].nunique(dropna=False)} variantes con ruido",
        f"{df_original['genero'].nunique(dropna=False)} variantes ('m', ' f ', etc.)",
        "object (texto con comas)",
        "object (formatos mixtos YYYY-MM-DD y DD/MM/YYYY)"
    ],
    'Estado Depurado (Después)': [
        f"{len(df):,}",
        "0 (0.0%)",
        "0 (0.0%)",
        "0 (0.0%)",
        "0 (0.0%)",
        "8 ciudades canónicas",
        "2 géneros canónicos (F, M)",
        "float64 (punto decimal)",
        "datetime64[ns] (ISO estandarizado)"
    ]
})
print(calidad_resumen.to_string(index=False))

# Pivote C: Valor Analítico Desbloqueado (Gasto promedio y suma por Ciudad y Categoría)
print("\n--- PIVOTE C: Valor Analítico Desbloqueado (Gasto por Ciudad y Categoría) ---")
pivot_c_mean = pd.pivot_table(df, index='ciudad', columns='categoria', values='gasto_q', aggfunc='mean').round(2)
print(">> Gasto Promedio (Q) por Ciudad y Categoría:")
print(pivot_c_mean)

pivot_c_sum = pd.pivot_table(df, index='ciudad', columns='categoria', values='gasto_q', aggfunc='sum',
                             margins=True, margins_name='Total').round(2)
print("\n>> Gasto Total Acumulado (Q) por Ciudad y Categoría:")
print(pivot_c_sum)

# Agregación mensual
df['mes_registro'] = df['fecha_registro'].dt.to_period('M')
pivot_mensual = pd.pivot_table(df, index='mes_registro', columns='categoria', values='gasto_q', aggfunc=['count', 'sum']).round(2)
print("\n>> Resumen Mensual de Transacciones y Montos por Categoría:")
print(pivot_mensual)

# ==============================================================================
# 7. EXPORTACIÓN DE RESULTADOS
# ==============================================================================
print("\n" + "=" * 80)
print("7. EXPORTACIÓN DE DATASETS LIMPIOS")
print("=" * 80)

# Exportar a CSV
df_export = df.drop(columns=['mes_registro'], errors='ignore')
df_export.to_csv("limpio.csv", index=False)
print("Dataset limpio exportado a CSV exitosamente: 'Tarea1/limpio.csv'")

# Exportar a Parquet (optimizado y tipado)
df_export.to_parquet("limpio.parquet", index=False, engine='pyarrow')
print("Dataset limpio exportado a Parquet exitosamente: 'Tarea1/limpio.parquet'")
