import pandas as pd

# cargamos el arcivo
df = pd.read_csv("dataset_sucio.csv")

df_original = df.copy()

print("Filas y columnas del archivo:", df.shape)
df.info()
# print(df.describe(include='all'))

# Obtenemos el número de duplicados
print("Duplicados encontrados:", df.duplicated().sum())

# Verlos antes de borrarlos
print(df[df.duplicated(keep=False)].sort_values('id_cliente').head(50))

# Eliminar los duplicados
df = df.drop_duplicates()
print("Forma después de eliminar duplicados:", df.shape)

# PARTE PARA LIMINAR NULOS
print("Cantidad e nulos")
print(df.isnull().sum())
# realizmos la eliminacion de los datos con nulos
df = df.dropna()

print()

print("Cantidad e nulos después de la eliminación:")
print(df.isnull().sum())

# PARTE PARA ESTANDARIZAR DATOS
# Eliminacion de espacios en blanco al inicio y al final de los datos
df['nombre'] = df['nombre'].str.strip(
).str.title().str.replace(r'\s+', ' ', regex=True)
df['genero'] = df['genero'].str.strip().str.upper()
df['ciudad'] = df['ciudad'].str.strip().str.title()
df['categoria'] = df['categoria'].str.strip().str.title()

# Convertimos los gastos que estan en string a float
df['gasto_q'] = df['gasto_q'].str.replace(',', '.', regex=False)
df['gasto_q'] = df['gasto_q'].astype(float)

# estadarizamo el formato de fecha
df['fecha_registro'] = pd.to_datetime(
    df['fecha_registro'], format='mixed', dayfirst=False)

df.info()

df.to_csv("limpio.csv", index=False)
