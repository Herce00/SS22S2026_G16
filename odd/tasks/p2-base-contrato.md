# p2-base-contrato — Base GCP y contrato de datos (Proyecto 2, Persona A)

## Objetivo

Primera parte independiente de Persona A: preparar la base en GCP y publicar la vista del contrato para que B empiece sin esperar.

## Problema y motivo

| Tema | Detalle |
|------|---------|
| Problema | B necesita datos limpios para BigQuery ML, pero la copia optimizada de A (`trips_2022_opt`) tardará. Si B espera, la pareja trabaja en serie. |
| Motivo | La vista `p2_contract.v_trips_clean` con esquema congelado desacopla a ambos: en la fase 1 lee la tabla pública y en la fase 2 apunta a la tabla optimizada sin que B cambie nada. |

## Alcance

| Incluido | Fuera de alcance (features posteriores de A) |
|----------|----------------------------------------------|
| Steering y convenciones del Proyecto 2 | EDA y vistas `v_eda_*` |
| Datasets `p2_a_trips`, `p2_contract`, `p2_b_ml` en `US` | Optimización: `trips_2022_std` y `trips_2022_opt` |
| Vista del contrato, fase 1, y sus validaciones | Fase 2 del contrato (cambio del `FROM`) |
| Permisos de B y mensaje de entrega | Todo el trabajo de ML y tablero (B) |

## Restricciones

- Proyecto GCP `ss2-g16-proyecto2`, ubicación `US`, crédito de prueba con USD 282 disponibles.
- Esquema y filtros exactamente como en [architecture.md](../../Proyecto_2/specs/steering/architecture.md#contrato-p2_contractv_trips_clean).
- Reglas de ejecución, costos y evidencia de [conventions.md](../../Proyecto_2/specs/steering/conventions.md).
- No se inventan cifras: toda cifra sale de una salida guardada.

## Entrega

| Atributo | Valor |
|----------|-------|
| Estrategia | `ask-on-risk` |
| Pronóstico | Unas 400 a 500 líneas de autoría, sobre todo documentación y SQL |
| Rama | `feat/p2-base-contrato` |

## Tareas

| ID | Tarea | Ruta de ejecución | Estado |
|----|-------|-------------------|--------|
| T1 | Steering y plan: `architecture.md`, `conventions.md`, este documento y `enunciado.md` como fuente | Writer delegado. Disparador: 3 documentos no triviales | [ ] |
| T2 | `Proyecto_2/sql/contract/00_datasets.sql`: crear los 3 datasets en `US`, ejecutarlo y guardar evidencia | Por definir | [ ] |
| T3 | `Proyecto_2/sql/contract/01_v_trips_clean.sql`: vista del contrato, fase 1. Validaciones en `Proyecto_2/sql/contract/02_validaciones_contrato.sql` | Por definir | [ ] |
| T4 | Dar a B lectura sobre `p2_contract` y escritura sobre `p2_b_ml` | Por definir | [ ] **Bloqueada:** falta el correo de B |
| T5 | Avisar a B con un mensaje breve que resuma el contrato | Por definir | [ ] |

## Criterios de aceptación

| ID | Criterio |
|----|----------|
| T1 | Los cuatro archivos están en un commit con mensaje Conventional Commit; los datos verificados coinciden con el perfil del 2026-10-25. |
| T2 | Los 3 datasets existen en `US`; la salida está guardada en `Proyecto_2/evidencia/`. |
| T3 | La vista existe y las validaciones muestran: al menos 1M de filas, esquema igual al del contrato, `trip_id` único y una muestra de 3 filtros sin violaciones. Salidas guardadas en `Proyecto_2/evidencia/`. |
| T4 | B consulta `p2_contract.v_trips_clean` y crea objetos en `p2_b_ml`; no puede escribir en `p2_a_trips` ni en `p2_contract`. |
| T5 | B confirma que recibió el mensaje, con nombre de la vista, columnas, filtros y split propuesto. |

## Verificación

| Tema | Regla |
|------|-------|
| Test-first | Excepción: no hay emulador local de BigQuery, así que no existe un RED ejecutable. La verificación es `--dry_run`, ejecución y archivo de evidencia guardado. |
| Revisión nativa | `gentle-ai review assess` sobre cada commit de trabajo cuando RDD está activo. |

## Progreso y evidencia

| ID | Commit | Evidencia | Revisión |
|----|--------|-----------|----------|
| T1 | Pendiente | Lectura estructural de los cuatro archivos | Pendiente |

## Siguiente paso

T2: escribir y ejecutar `00_datasets.sql`.
