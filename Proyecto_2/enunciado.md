Procesamiento y Análisis Exploratorio 
de Datos Masivos en BigQuery

2. 
Resumen Ejecutivo 
En esta fase, los estudiantes trabajarán con el dataset público New York City Taxi Trips 2022, 
disponible en Google BigQuery, que contiene más de 100 millones de registros de viajes de 
taxi en la ciudad de Nueva York. 
El proyecto busca desarrollar competencias en análisis exploratorio de datos masivos 
utilizando SQL en BigQuery, aplicando técnicas de transformación y optimización de 
consultas mediante particiones y clustering, y comunicando hallazgos relevantes mediante 
visualizaciones iniciales.  
Utilizando BigQuery ML, se entrenarán al menos 2 modelos distintos de regresión o 
clasificación, se evaluará su desempeño mediante métricas como precisión, error cuadrático 
medio o matriz de confusión, y se aplicará sobre nuevos datos. Finalmente, se construirá un 
tablero en Google Data Studio para comunicar visualmente los resultados y sus 
implicaciones. 
3. 
Enunciado del Proyecto 
3.1 Descripción del problema a resolver 
El análisis de grandes volúmenes de datos representa un reto cuando las consultas son 
lentas, costosas o difíciles de interpretar. En este proyecto se utilizará el dataset público NYC 
Taxi Trips 2022 en BigQuery, con más de 100 millones de registros, para transformar datos 
masivos en información útil. 
El estudiante deberá diseñar consultas SQL, aplicar técnicas de optimización mediante 
particiones y clustering, identificar patrones significativos de viaje, costo y comportamiento de 
usuarios, y presentar hallazgos mediante visualizaciones exploratorias claras. 
3.2 Alcance del proyecto 
Obligatorio: 
● Conectarse al dataset público 
bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022. 
● Realizar consultas SQL avanzadas para calcular métricas descriptivas, analizar 
distribuciones categóricas y detectar patrones temporales. 
● Crear tablas derivadas en su propio proyecto para trabajar subconjuntos optimizados 
del dataset. 
● Implementar particiones por fecha y clustering por ubicaciones para reducir el costo 
de procesamiento. 
● Comparar el rendimiento de las consultas antes y después de aplicar optimización. 
● Exportar o enlazar resultados a Google Sheets o Looker Studio para generar al menos 
3 visualizaciones exploratorias.

 Documentar el proceso en un repositorio organizado, incluyendo scripts SQL, 
capturas de consultas, evidencias e informe visual. 
● Usar BigQuery ML para entrenar al menos 2 modelo predictivo sobre un dataset 
limpio. 
● Implementación y comparación entre modelos con distintas métricas de evaluación e 
hiperparametros (como ROC-AUC, RMSE, matriz de confusión o iteraciones)  
● Manejo de data leakage por data_split_eval_fraction y split personalizado. 
● Ejecutar predicciones sobre nuevos registros. 
● Representar resultados y hallazgos de los modelos mediante visualizaciones en el 
dashboard. 
3.3 Requerimientos técnicos 
● Herramientas: Google Cloud Platform (GCP), Google BigQuery, Google Sheets o 
Looker Studio y GitHub. 
● Dataset: bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022. 
● Consultas: uso de funciones agregadas, funciones temporales, filtros, agrupaciones 
y transformaciones SQL. 
● Optimización: implementación de particiones (definido por el estudiante) y 
clustering (definido por el estudiante). 
● Conocimientos aplicados: análisis exploratorio de datos masivos, optimización de 
consultas y comunicación visual de hallazgos. 
3.4 Entregables 
Tipo 
Scripts SQL 
Descripción 
Archivo(s) .sql con las consultas realizadas en BigQuery para 
exploración, transformaciones y optimización. Deben estar 
comentados para explicar la finalidad de cada bloque. 
Scripts Big Query 
ML  
Script SQL del modelo entrenado y evaluado y tablas de resultados 
con predicciones. 
Evidencias 
Capturas de pantalla de consultas relevantes en BigQuery, conteo de 
registros, aplicación de particiones/clustering y evidencia de 
reducción de bytes procesados. 


Informe visual Enlace a un tablero de Looker Studio o archivo de Google Sheets 
enlazado a BigQuery, con al menos 3 visualizaciones exploratorias 
de hallazgos clave y la comparación de al menos 2 predicciones con 
los modelos de ML (Rolling Forecast) 
Archivo README Documento técnico con nombre del proyecto, dataset utilizado, 
transformaciones realizadas, técnicas de optimización aplicadas, 
comparación de desempeño (optimizado vs estándar),  hallazgos 
relevantes, explicación de los modelos de regresión o clasificación 
en BigQuery ML, enlace al informe visual. 
Repositorio del 
curso 
Carpeta Proyecto_2 dentro del repositorio SS22S2026_#GRUPO, 
que contenga todos los archivos del proyecto, documentación y 
scripts organizados conforme a los lineamientos del laboratorio. En el 
README deben indicarse ambos integrantes de la pareja. 


4. Material de apoyo 
● Documentación oficial de BigQuery https://cloud.google.com/bigquery/docs 
● Documentación de BigQuery Public Datasets 
https://cloud.google.com/bigquery/public-data 
● Guías de particiones, clustering y Looker Studio 
https://cloud.google.com/bigquery/docs/partitioned-tables 
 
5. Metodología 
1. Conexión y exploración inicial del dataset: 
 Acceder al dataset público en BigQuery, validar registros y comprender la estructura de las 
tablas y variables disponibles. 
2. Desarrollo de consultas SQL y transformaciones: 
 Construir consultas para filtrar, agrupar, calcular métricas y preparar datos útiles para el 
análisis exploratorio. 
3. Optimización del procesamiento: 
 Crear tablas derivadas, aplicar particiones y clustering, y comparar costos de procesamiento 
antes y después de la optimización. 
4. Visualización y análisis de hallazgos: 
 Generar visualizaciones exploratorias en Google Sheets o Looker Studio para resumir 
patrones clave del dataset. 

vidad el enlace al repositorio de GitHub que contiene la carpeta Proyecto_2.

Verificar que el enlace permita revisar los archivos, scripts, evidencias, documentación y resultados correspondientes.