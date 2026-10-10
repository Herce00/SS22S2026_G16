# Proyecto 1: Pipeline ELT con Python, Apache Airflow, dbt y PostgreSQL

## Resumen Ejecutivo
Este proyecto, desarrollado en el curso Seminario de Sistemas 2, tiene como propósito implementar una solución completa de integración, transformación y modelado analítico de datos utilizando Python, Apache Airflow, dbt y PostgreSQL. El problema identificado es la necesidad de automatizar la extracción desde una fuente transaccional, cargar datos crudos en un Data Warehouse, transformar la información de forma controlada y construir modelos analíticos confiables. La propuesta consiste en desarrollar un flujo ELT orquestado con Airflow, procesos de extracción y carga con Python, un Data Warehouse en PostgreSQL y modelos dbt para staging, dimensiones, hechos, pruebas y documentación. El proyecto deberá desarrollarse en parejas y permitirá aplicar competencias en ingeniería de datos, modelado dimensional, automatización, calidad de datos y documentación técnica profesional.

---

## 3. Enunciado del Proyecto

### 3.1 Descripción del problema a resolver
SG-Food es una empresa dedicada a la distribución y comercialización de productos de diversas marcas y categorías. Actualmente enfrenta dificultades para integrar y analizar sus datos debido a procesos manuales, poca trazabilidad en las transformaciones, ausencia de pruebas de calidad y dependencia directa de la base de datos transaccional para la generación de reportes.

Las parejas deberán desarrollar una solución moderna de datos que permita automatizar el flujo desde una base transaccional hacia un Data Warehouse en PostgreSQL. La solución debe utilizar Python para la extracción y carga de datos, Apache Airflow para la orquestación del pipeline y dbt para transformar, documentar y validar los modelos analíticos. El objetivo es disponer de una arquitectura reproducible que integre datos crudos, construya dimensiones y hechos, ejecute pruebas de calidad y facilite consultas analíticas para la toma de decisiones oportunas.

### 3.2 Alcance del proyecto

#### Obligatorio:
- Implementar un proceso de extracción y carga utilizando Python.
- Orquestar el flujo completo mediante Apache Airflow, incluyendo tareas de carga, ejecución de dbt y validaciones.
- Desarrollar un Data Warehouse en PostgreSQL con modelo dimensional basado en tablas de hechos y dimensiones.
- Implementar modelos dbt para staging, intermediate y marts, incluyendo sources, refs, materializaciones y pruebas de calidad.
- Validar y documentar el flujo completo: extracción, carga raw, modelos dbt, Data Warehouse analítico y consultas de validación.

#### Opcional / Recomendado:
- Incluir ejecución programada del DAG de Airflow y parametrización de conexiones mediante variables o archivos de configuración.
- Implementar validaciones adicionales, manejo de errores y registros de ejecución dentro del flujo de Airflow y dbt.
- Conectar los modelos analíticos de PostgreSQL con una herramienta de visualización como Power BI, Metabase o Superset.

### 3.3 Requerimientos técnicos
- **Herramientas de desarrollo:** Python, Apache Airflow, dbt Core y PostgreSQL.
- **Plataforma de datos:** PostgreSQL como Data Warehouse y schemas separados para raw, staging y marts.
- **Fuentes de datos:** al menos una base de datos transaccional y archivos delimitados o CSV cargados mediante Python.
- **Procesos requeridos:** extracción, carga, orquestación, transformación con dbt, pruebas de calidad y validación de consultas analíticas.
- **Modelo de datos:** esquema dimensional o estrella en PostgreSQL, construido con dbt mediante dimensiones, hechos, relaciones y materializaciones consistentes.
- **Conocimientos aplicados:** Python, Airflow, ELT, Data Warehouse, dbt, modelado dimensional, pruebas de calidad y documentación técnica.

---

## Entregables

| Tipo | Descripción |
| :--- | :--- |
| **Proyecto de Python, Airflow y dbt** | Solución completa con scripts Python, DAGs de Airflow, proyecto dbt y configuración necesaria para ejecutar la extracción, carga, transformación, validación y documentación del flujo de datos. |
| **Script DDL del Data Warehouse** | Archivo con las sentencias SQL para la creación de schemas, tablas raw si aplica, tablas de hechos, dimensiones, relaciones y claves necesarias para el Data Warehouse implementado en PostgreSQL. |
| **Scripts de validación y consultas analíticas** | Archivos SQL, pruebas dbt y consultas analíticas utilizadas para comprobar la correcta carga de datos, validar la integridad de la información y verificar resultados de los modelos analíticos. |
| **Documentación técnica** | Documento o archivo README que incluya el nombre del proyecto, integrantes de la pareja, descripción del pipeline, DAG de Airflow, modelo del Data Warehouse, estructura del proyecto dbt, justificación de diseño y manual de implementación. |

---

## 4. Material de apoyo
- Documentación oficial de Apache Airflow: [https://airflow.apache.org/docs/](https://airflow.apache.org/docs/)
- Documentación oficial de dbt: [https://docs.getdbt.com/](https://docs.getdbt.com/)
- Documentación oficial de PostgreSQL: [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)
- Guía de instalación de dbt para PostgreSQL: [https://docs.getdbt.com/docs/core/connect-data-platform/postgres-setup](https://docs.getdbt.com/docs/core/connect-data-platform/postgres-setup)

---

## 5. Metodología

### 1. Investigación preliminar
Analizar el contexto de la empresa SG-Food y revisar los conceptos clave de ingeniería de datos, Data Warehouse, ELT, orquestación con Airflow y modelado analítico con dbt. Identificar las fuentes de datos y definir las estructuras necesarias para la carga raw y la transformación analítica.

### 2. Diseño del sistema de datos
Definir la arquitectura general del sistema. Diseñar el flujo de extracción y carga con Python, el DAG de Airflow, la estructura del Data Warehouse en PostgreSQL y el modelo dimensional que será construido con dbt, incluyendo sources, staging, dimensiones, hechos, pruebas y documentación.

### 3. Desarrollo del proceso de extracción y carga
Implementar con Python los procesos de conexión a la fuente, extracción de datos, limpieza técnica mínima y carga hacia el schema raw de PostgreSQL. Integrar estas tareas en Apache Airflow para asegurar ejecución ordenada, trazabilidad y control de errores.

### 4. Implementación del Data Warehouse y modelos dbt
Construir los modelos dbt necesarios para transformar los datos raw en staging, intermediate y marts. Crear tablas de dimensiones y hechos, aplicar llaves, relaciones, materializaciones, pruebas y documentación automática del proyecto.

### 5. Validación y pruebas
Ejecutar pruebas funcionales para verificar conteos de registros, integridad referencial, unicidad, valores nulos, consistencia de los modelos dbt y resultados de consultas analíticas. Documentar los resultados obtenidos y realizar los ajustes necesarios.

### 6. Documentación y entrega final
Elaborar un documento técnico que describa todas las fases del proyecto, incluyendo arquitectura, DAG de Airflow, scripts Python, estructura de PostgreSQL, modelos dbt, pruebas, consultas de validación y manual de implementación. Subir al repositorio correspondiente todos los archivos requeridos en la carpeta `Proyecto1`.

---

## 6. Recursos y herramientas a utilizar

### Software
- Python 3.x
- Apache Airflow
- PostgreSQL y dbt Core con adapter dbt-postgres

### Plataformas
- GitHub (para repositorio del proyecto y control de versiones)
- UEDI (para entrega oficial del proyecto)

### Lenguajes y tecnologías
- Python (para extracción, carga y scripts auxiliares)
- Apache Airflow (para orquestación del pipeline)
- SQL y dbt (para modelado analítico, pruebas, documentación y materializaciones)

### Lecturas recomendadas
- Documentación de Apache Airflow
- Documentación de dbt Core y dbt-postgres
- Guías de modelado dimensional, fuentes, pruebas y materializaciones en dbt
- Artículos sobre validación, observabilidad, calidad de datos y buenas prácticas ELT

---

## Criterios de Aceptación

| Tema | Descripción | Cumple |
| :--- | :--- | :---: |
| **Cumplimiento de la tecnología establecida** | El desarrollo debe realizarse utilizando Python, Apache Airflow, PostgreSQL y dbt como componentes obligatorios del flujo completo. | [ ] |
| **Uso de herramientas requeridas** | Se debe evidenciar el uso de scripts Python funcionales, DAGs de Airflow, carga en PostgreSQL, implementación de modelos dbt, pruebas de calidad y validación mediante consultas SQL. | [ ] |
| **Gestión y entregas del proyecto** | El repositorio `SS22S2026_#GRUPO` debe contener la carpeta `Proyecto1` con todos los archivos: scripts Python, DAGs de Airflow, proyecto dbt, scripts SQL, documentación técnica y evidencia de ejecución. El trabajo debe realizarse en parejas. | [ ] |
| **Documentación obligatoria** | Debe incluir un documento o README con la descripción del proceso de extracción y carga, el Data Warehouse, los modelos dbt implementados, la justificación del diseño, integrantes de la pareja y un manual de implementación. | [ ] |
| **Pruebas y funcionalidad mínima** | El sistema debe ejecutar correctamente el DAG de Airflow, cargar datos desde las fuentes establecidas, ejecutar modelos dbt, correr pruebas de calidad y permitir la validación de resultados mediante consultas analíticas. | [ ] |

---

## Rúbrica de Evaluación (Checklist)

### 1. Habilidades
- [ ] Desarrollo del flujo de extracción y carga con Python y orquestación con Airflow.
- [ ] Documentación técnica y manual de implementación.
- [ ] Cumplimiento de entregables, trabajo en parejas y organización del repositorio.

### 2. Conocimientos
- [ ] Diseño e implementación del Data Warehouse en PostgreSQL y modelos analíticos en dbt.
- [ ] Integración de fuentes, pruebas dbt y validación del flujo completo.