# p2-a-readme — Documentación técnica del Proyecto 2 (Persona A)

## Objetivo

Redactar en `Proyecto_2/README.md` todas las secciones técnicas correspondientes a Persona A exigidas por el enunciado del proyecto (identificación de integrantes, dataset utilizado, transformaciones y saneamiento de datos, técnicas de optimización aplicadas, comparación formal de rendimiento estándar vs. optimizado y síntesis estructurada de hallazgos del EDA), asegurando paridad numérica estricta con las evidencias guardadas en `Proyecto_2/evidencia/`.

## Problema y motivo

| Tema | Detalle |
|------|---------|
| Problema | El enunciado exige un documento técnico README con descripción del proyecto, dataset, transformaciones, optimización, comparación de desempeño y hallazgos relevantes. |
| Motivo | Persona A concluyó la ingesta, contrato, optimización y EDA; el README sintetiza estos resultados con rigor arquitectónico y cuantitativo, dejando preparadas las secciones reservadas para Persona B (BigQuery ML y tablero de Looker Studio). |

## Alcance

| Incluido | Fuera de alcance (Persona B) |
|----------|------------------------------|
| Identificación del grupo e integrantes | Modelos predictivos en BigQuery ML |
| Dataset utilizado y contexto de la fuente pública | Métricas de evaluación de ML (RMSE, ROC-AUC) |
| Transformaciones y contrato de datos | Split personalizado y predicciones sobre nuevos datos |
| Técnicas de optimización (particionamiento y clustering) | Enlace y capturas del tablero en Looker Studio |
| Comparación formal estándar vs. optimizado (Q1–Q4) | |
| Síntesis integral de hallazgos del EDA (5 ejes) | |
| Vistas analíticas publicadas en `p2_a_trips` | |

## Restricciones

- Paridad numérica estricta: toda cifra debe coincidir con las evidencias `01_datasets.txt` a `10_vistas_eda.txt`.
- Nunca inventar cifras ni interpretaciones sin sustento. Hipótesis marcadas como "(hipótesis)".
- Redacción técnica en español profesional y neutral, manteniendo la coherencia con los documentos del repositorio.
- Commits bajo la norma `<tipo>: <descripción en español ≤50>`, sin trailers de IA ni Co-Authored-By.

## Tareas

| ID | Tarea | Ruta de ejecución | Estado |
|----|-------|-------------------|--------|
| T1 | Este plan | Inline: un documento | [x] Este commit |
| T2 | Redacción técnica de las secciones de Persona A en `Proyecto_2/README.md` | Writer delegado | [x] |

## Progreso y evidencia

| ID | Commit | Evidencia | Revisión |
|----|--------|-----------|----------|
| T1 | `2954ed9` | `odd/tasks/p2-a-readme.md` | Omitido (plan) |
| T2 | `875cbdb` | `Proyecto_2/README.md`: carátula, arquitectura, dataset (36.26M filas / 7.49 GB, 335 días), saneamiento (34,796,108 filas, -4.03 %), optimización (particiones diarias + clustering), comparación formal de rendimiento (Q1 -97.75 %, Q3 -91.10 %), síntesis integral de hallazgos en 5 ejes cuantitativos, catálogo de 4 vistas analíticas y estructura preparada para Persona B | `medium` / `slice_budget_reached` → omitido según plan del usuario (revisión al final) |

## Siguiente paso

Feature de entrega a Persona B (César): configuración IAM y mensaje de entrega.
