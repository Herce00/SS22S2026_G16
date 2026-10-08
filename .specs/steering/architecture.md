# Arquitectura y límites de trabajo — Proyecto 1 (SG-Food)

Pipeline ELT para SG-Food: Python extrae y carga a `raw`, dbt transforma hacia `staging` y `marts`, y Airflow orquesta todo sobre PostgreSQL. Este documento fija las reglas arquitectónicas y **qué puede editar cada integrante, qué debe discutirse antes y qué no le corresponde tocar**.

Es válido para los dos integrantes. No asume un rol: quien lo use debe identificar el suyo primero.

- **Fuente de requisitos:** [Proyecto1/enunciado.md](../../Proyecto1/enunciado.md)
- **Documentos hermanos:** [tech-stack.md](tech-stack.md) · [coding-standards.md](coding-standards.md)

## Cómo usar este documento

1. Identificar el rol activo en la tabla de roles. Un agente o asistente **no debe asumirlo**: si la sesión no lo declara, se pregunta.
2. Ubicar la ruta o el tema a modificar en el [mapa de propiedad](#mapa-de-propiedad).
3. Aplicar la [regla de zonas](#regla-de-zonas) según quién es el dueño.

## Roles

| Rol | Integrante | Foco | Rama |
|-----|-----------|------|------|
| **A** — Ingesta y orquestación | Keneth Willard Lopez Ovalle — `202100106` | Infraestructura, DDL de `raw`, Python, Airflow | `feat/ingesta-airflow` |
| **B** — Transformación y modelado | César Rolando Hernández Palacios — `202000806` | dbt, modelo dimensional, pruebas, consultas analíticas | `feat/dbt-modelado` |

Ambos deben poder explicar y defender el pipeline completo en la calificación.

## Flujo de datos

```
BD transaccional ──┐
                   ├─► Python (extract + load) ─► raw ─► dbt staging ─► dbt intermediate ─► dbt marts
Archivos CSV ──────┘                                                                          │
                                                                                              ▼
                              Airflow orquesta: carga → dbt run → dbt test → validaciones   Consultas analíticas
```

| Capa | Schema PostgreSQL | La escribe | Dueño |
|------|-------------------|-----------|-------|
| Fuente | BD transaccional + CSV | Datos de origen | A |
| Raw | `raw` | Scripts Python | A |
| Staging | `staging` | dbt | B |
| Intermediate | `staging` o schema propio (lo define B) | dbt | B |
| Marts | `marts` | dbt | B |

## Reglas arquitectónicas

1. **ELT, no ETL.** Python solo extrae, hace limpieza técnica mínima y carga. Las reglas de negocio viven en dbt.
2. **Limpieza técnica mínima** significa: codificación, delimitadores, nombres de columna normalizados, filas vacías y columnas de auditoría. No incluye deduplicar por negocio, imputar valores ni derivar columnas.
3. **`raw` es fiel a la fuente.** No se filtran ni corrigen registros; los datos sucios llegan a `raw` y se tratan en `staging`.
4. **Un solo sentido de dependencia.** `raw → staging → intermediate → marts`. Python nunca escribe en `staging` ni `marts`; dbt nunca escribe en `raw`.
5. **dbt lee `raw` solo mediante `source()`** y el resto mediante `ref()`. Nada de nombres de tabla escritos a mano.
6. **El contrato raw es la interfaz entre A y B.** Tablas y columnas de `raw` no cambian sin acuerdo de ambos.
7. **Cargas idempotentes.** Reejecutar el DAG no debe duplicar filas en `raw`.
8. **Sin credenciales en el repositorio.** Todo parámetro de conexión entra por variables de entorno o conexiones de Airflow.
9. **Reproducible con un comando.** `docker compose up` debe levantar el entorno completo desde cero.
10. **Airflow orquesta, no transforma.** Las tareas invocan scripts Python y comandos dbt; la lógica no vive dentro del DAG.
11. **El diseño no depende del archivo de datos.** La ingesta se guía por configuración: la llegada de los datos reales cambia configuración y contrato, no código.

## Decisiones acordadas

| # | Tema | Decisión | Motivo |
|---|------|----------|--------|
| D1 | Datos de origen | Ingesta guiada por un archivo de configuración que declara cada fuente y su tabla `raw` destino. Hasta recibir el archivo oficial se trabaja con datos de muestra mínimos. | El curso entregará los datos más adelante y pide no esperar para avanzar. |
| D2 | Motor de la BD fuente | PostgreSQL en un contenedor separado del DW, poblado por un script de inicialización. | Un solo motor y un solo driver. |
| D3 | Contrato raw | Vive en `Proyecto1/docs/contrato_raw.md`. Inicia como `v0` (borrador) y pasa a `v1` al llegar los datos reales. | B puede desarrollar `sources.yml` y `staging` desde el primer día. |
| D4 | Tipado en `raw` | Todas las columnas de negocio como `TEXT`, más las columnas de auditoría `_loaded_at` y `_source`. El tipado se hace en `staging`. | Sin conocer los datos, una carga a texto no falla por formatos inesperados. |
| D5 | Estrategia de carga | Truncar y recargar dentro de una transacción. | Idempotente sin depender de claves o fechas aún desconocidas. |
| D6 | dbt desde Airflow | `BashOperator` con `dbt run` y `dbt test`. | Sin dependencias adicionales. |
| D7 | Versiones | Se verifican contra la documentación oficial al construir el entorno y se fijan en [tech-stack.md](tech-stack.md). | Evitar incompatibilidades entre Airflow, Python y dbt. |

Consecuencias que cada rol debe tener presentes:

- **D1 — datos de muestra.** Sirven solo para desarrollar. No pueden aparecer en la evidencia ni en las cifras del README.
- **D1 y D2 — forma del archivo oficial.** El enunciado exige una BD transaccional y además archivos CSV. Si el curso entrega un único archivo plano, A lo divide: una parte se siembra en la BD fuente y otra se conserva como CSV.
- **D4 — tipado.** Todo el trabajo de conversión de tipos y manejo de formatos recae en los modelos `staging` de B.
- **D5 — incremental.** B puede usar materializaciones incrementales en dbt aunque la carga a `raw` sea completa.

Cambiar una decisión acordada es un tema de zona amarilla.

## Mapa de propiedad

| Ruta o tema | Dueño | Contenido |
|-------------|-------|-----------|
| `Proyecto1/docker-compose.yml`, `Proyecto1/.env.example` | A | DW, BD transaccional fuente y Airflow |
| `Proyecto1/sql/ddl/` | A | Schemas `raw`, `staging`, `marts` y tablas de `raw` |
| `Proyecto1/python/` | A | Extracción, carga de CSV, limpieza técnica, configuración de fuentes |
| `Proyecto1/airflow/dags/` | A | DAG: tareas, dependencias, reintentos, errores, logs, programación |
| Datos de muestra y script de inicialización de la BD fuente | A | Insumos de desarrollo hasta recibir el archivo oficial |
| `Proyecto1/dbt_project/**` | B | `sources.yml`, modelos, pruebas, macros, documentación dbt |
| Diseño del modelo dimensional | B | Hechos, dimensiones, granularidad, bus matrix |
| `Proyecto1/sql/validaciones/` y consultas analíticas | B | Conteos, integridad referencial, resultados de negocio |
| README: pipeline, DAG, Python, manual de implementación | A | B revisa |
| README: modelo del DW, estructura dbt, justificación de diseño | B | A revisa |
| `Proyecto1/evidencia/` | Cada uno la de su parte | Capturas y logs de ejecución |
| `Proyecto1/docs/contrato_raw.md` | Compartido | A propone, B valida |
| `.specs/steering/` | Compartido | Estos documentos |

## Regla de zonas

La zona se determina respecto al rol activo.

| Zona | Cuándo aplica | Qué se permite |
|------|--------------|----------------|
| **Verde** | La ruta es del rol activo y el cambio no toca un tema compartido | Editar libremente |
| **Amarilla** | El tema está en la lista de temas compartidos, aunque el archivo sea propio | Leer, revisar y proponer. Editar solo con acuerdo del otro integrante |
| **Roja** | La ruta es del otro rol, o está en la lista de exclusiones | Solo lectura y revisión por pull request |

### Temas compartidos (zona amarilla para ambos)

| Tema | Por qué es compartido | Quién decide |
|------|----------------------|--------------|
| Contrato raw: tablas, columnas, columnas de auditoría | A lo carga, B lo consume desde `sources.yml` | A propone, B valida |
| Nombres de schemas y de la base de datos | Los usan el DDL, `profiles.yml` y los modelos | Ambos |
| Nombres de variables de entorno de conexión | Los comparten Python, Airflow y dbt | Ambos |
| Tarea del DAG que ejecuta `dbt run` y `dbt test` | La tarea es de A; comandos, selectores y orden son de B | A implementa, B define |
| Tarea de validaciones por conteo | La tarea es de A; reutiliza SQL de B | A implementa, B revisa |
| Decisiones acordadas D1 a D7 | Condicionan el trabajo de los dos | Ambos |
| Estructura de carpetas de `Proyecto1/` y del README | Entregable único de la pareja | Ambos |
| Versiones fijadas y dependencias Python que afectan a dbt | dbt corre en el entorno que construye A | Ambos |
| Estos documentos de `.specs/steering/` | Rigen el trabajo de los dos | Ambos |

### Exclusiones (zona roja para ambos)

| Ruta o acción | Motivo |
|---------------|--------|
| `Tarea1/`, `Practica1/`, `Practica2/` | Entregas anteriores ya calificadas |
| Push directo a `main` | Todo entra por pull request revisado por el otro integrante |
| Push, rebase o `--force` sobre la rama del otro | Cada rama tiene un único autor |

### Qué hacer al encontrar un defecto en zona roja

Se reporta al dueño con evidencia (archivo, línea, consulta o comando que lo reproduce) y se propone el cambio. No se corrige por cuenta propia, aunque el arreglo sea trivial.

**Apoyo cruzado:** si un integrante termina antes, puede ayudar en la parte del otro, pero solo a pedido del dueño y mediante pull request hacia su rama.

## Puntos de integración

| # | Punto | Entrega A | Entrega B |
|---|-------|-----------|-----------|
| 1 | Contrato raw `v0` | Propuesta de tablas y columnas | Validación |
| 2 | Entorno | `docker compose up` funcional con los tres schemas creados | Proyecto dbt que se conecta al DW |
| 3 | Datos de muestra en `raw` | DAG de carga funcionando | `sources.yml`, `staging` y `marts` sobre la muestra |
| 4 | dbt en el DAG | Tareas `dbt run` y `dbt test` | Proyecto ejecutable y comandos definidos |
| 5 | Validaciones | Tarea de conteos en el DAG | Consultas de validación y analíticas |
| 6 | Datos oficiales | Configuración de fuentes y contrato `v1` | Ajuste de modelos y pruebas |
| 7 | Cierre | README de ingesta y evidencias | README de modelado, evidencias, `dbt docs` |

## Pendientes

- [ ] Recibir el archivo de datos oficial y definir cómo se reparte entre BD transaccional y CSV.
- [ ] Redactar y validar el contrato raw `v0`.
- [x] Verificar y fijar las versiones del entorno (D7).
- [ ] Definir dónde se materializa la capa intermediate (B).
