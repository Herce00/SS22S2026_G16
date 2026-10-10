# Requisitos — `dag-orquestacion`

DAG de Airflow que ejecuta el pipeline completo en orden: carga a `raw`, validación de la carga, `dbt run`, `dbt test` y validaciones finales. Es la última feature del rol A y la que une el trabajo de los dos integrantes.

- **Rol dueño:** A (ingesta y orquestación). Las tareas de dbt y de validación final son tema compartido: A implementa, B define.
- **Steering:** [architecture.md](../../steering/architecture.md) · [tech-stack.md](../../steering/tech-stack.md) · [coding-standards.md](../../steering/coding-standards.md)
- **Feature anterior:** [ingesta-raw](../ingesta-raw/requirements.md)
- **Siguientes documentos:** [design.md](design.md) · [tasks.md](tasks.md)

## Problema

La carga a `raw` funciona, pero se ejecuta a mano y nada la encadena con dbt. El enunciado exige orquestar con Airflow el flujo completo, con tareas de carga, ejecución de dbt y validaciones, ejecución ordenada, trazabilidad y control de errores.

## Casos de uso

| ID | Actor | Caso de uso | Resultado |
|----|-------|-------------|-----------|
| CU1 | Cualquier integrante | Ejecutar el pipeline completo desde la interfaz de Airflow | Todas las tareas terminan bien y `marts` queda actualizado |
| CU2 | Airflow | Ejecutar el pipeline de forma programada | Una ejecución diaria, sin solaparse con otra |
| CU3 | Rol A | Diagnosticar una ejecución fallida | El registro de la tarea muestra la causa; las tareas posteriores no corrieron |
| CU4 | Rol A | Reintentar una carga que falló por una causa transitoria | Airflow reintenta solo esa tarea |
| CU5 | Rol B | Cambiar los modelos o las pruebas dbt | El DAG los ejecuta sin modificar el código del DAG |
| CU6 | Rol B | Agregar una validación SQL final | El DAG la ejecuta con solo agregar el archivo |
| CU7 | Evaluador | Ver el grafo y una ejecución exitosa | Evidencia del flujo completo |

## Alcance

**Incluye:**

- DAG `sgfood_elt` con tareas de carga, validación de carga, `dbt run`, `dbt test` y validaciones finales.
- Función de validación de conteos entre cada fuente y su tabla en `raw`.
- Mecanismo para ejecutar las validaciones SQL finales que entregue B.
- Reintentos, tiempos límite, dependencias y control de concurrencia.
- Programación diaria (requisito opcional del enunciado).
- Pruebas de estructura y de ejecución del DAG, con proyectos dbt mínimos de prueba.
- Esqueleto del proyecto dbt real, para que B arranque con el proyecto conectado y ejecutable (decisión D11).
- Guía de arranque para B.
- Evidencia de una ejecución completa y sección del README.

**No incluye:**

| Fuera de alcance | Dónde va |
|------------------|----------|
| Modelos de negocio, diseño dimensional y pruebas del proyecto dbt | Rol B |
| Contenido de las validaciones SQL finales y consultas analíticas | Rol B |
| Cambios a la ingesta o al contrato raw | Features anteriores |
| Alertas por correo u otros canales | No requerido |
| Herramienta de visualización | Opcional, rol B |

## Requisitos (EARS)

### R1 — Estructura del DAG

- **R1.1** El sistema deberá definir un único DAG llamado `sgfood_elt` en `Proyecto1/airflow/dags/`.
- **R1.2** El DAG deberá contener una tarea de carga por cada fuente declarada en `fuentes.yml`.
- **R1.3** El DAG deberá ejecutar, en este orden: cargas a `raw`, validación de la carga, `dbt run`, `dbt test` y validaciones finales.
- **R1.4** Cuando se agregue una fuente a `fuentes.yml`, el DAG deberá incluir su tarea de carga sin modificar el archivo del DAG.
- **R1.5** El archivo del DAG no deberá contener lógica de extracción, carga ni transformación.

### R2 — Carga a `raw`

- **R2.1** Cada tarea de carga deberá invocar la función pública de `sgfood_ingesta` para su tabla.
- **R2.2** Todas las tareas de carga de una misma ejecución deberán usar el mismo valor de `_loaded_at`.
- **R2.3** Si una tarea de carga falla, entonces el sistema deberá reintentarla antes de marcarla como fallida.

### R3 — Validación de la carga

- **R3.1** Cuando todas las cargas terminen, el sistema deberá comparar la cantidad de filas de cada tabla de `raw` con la cantidad de filas de su fuente en ese momento.
- **R3.2** Si alguna cantidad no coincide, entonces la tarea deberá fallar indicando la tabla y ambas cantidades.
- **R3.3** La tarea deberá registrar la cantidad de filas por tabla y el total.

### R4 — Ejecución de dbt

- **R4.1** Cuando la validación de la carga termine bien, el sistema deberá ejecutar `dbt run` y después `dbt test` sobre el proyecto de `DBT_PROJECT_DIR`.
- **R4.2** El sistema deberá ejecutar dbt con el ejecutable del entorno virtual aislado.
- **R4.7** Cuando el proyecto dbt declare paquetes, el sistema deberá instalarlos antes de `dbt run`.
- **R4.3** Si `dbt run` falla, entonces el sistema no deberá ejecutar `dbt test`.
- **R4.4** Si una prueba dbt falla, entonces la tarea `dbt_test` deberá fallar.
- **R4.5** La salida completa de dbt deberá quedar en el registro de la tarea.
- **R4.6** El DAG no deberá fijar modelos ni selectores propios de B en su código; los comandos deberán poder ajustarse sin editar la lógica del DAG.

### R5 — Validaciones finales

- **R5.1** Cuando `dbt test` termine bien, el sistema deberá ejecutar cada consulta de validación de la carpeta acordada con B.
- **R5.2** Si una consulta de validación devuelve filas, entonces la tarea deberá fallar registrando el archivo y las filas devueltas.
- **R5.3** Si la carpeta no contiene validaciones, entonces la tarea deberá terminar bien registrando una advertencia explícita.
- **R5.4** Cuando se agregue un archivo de validación, el DAG deberá ejecutarlo sin modificar el archivo del DAG.

### R6 — Control de errores y concurrencia

- **R6.1** Si una tarea falla de forma definitiva, entonces el sistema no deberá ejecutar las tareas que dependen de ella.
- **R6.2** El sistema no deberá ejecutar dos ejecuciones del DAG al mismo tiempo.
- **R6.3** Cada tarea deberá tener un tiempo límite de ejecución.
- **R6.4** El sistema no deberá reintentar `dbt test` ni las validaciones: sus fallos indican un problema de datos, no uno transitorio.

### R7 — Programación

- **R7.1** El DAG deberá estar programado para ejecutarse una vez al día.
- **R7.2** El DAG no deberá ejecutar periodos anteriores al activarse.
- **R7.3** El DAG deberá crearse en pausa, de modo que levantar el entorno no dispare ejecuciones.

### R8 — Operación

- **R8.1** El DAG deberá cargarse en Airflow sin errores de importación.
- **R8.2** El DAG deberá tomar las conexiones y rutas desde el entorno o desde Airflow, sin valores escritos en el archivo.
- **R8.3** El sistema deberá permitir indicar, al disparar una ejecución, un proyecto dbt y una carpeta de validaciones distintos de los predeterminados.

### R9 — Esqueleto del proyecto dbt

- **R9.1** El repositorio deberá contener en `Proyecto1/dbt_project/` un proyecto dbt mínimo que se conecte al DW con las variables `DW_*`, sin credenciales escritas.
- **R9.2** El esqueleto deberá declarar como fuentes las 12 tablas de `raw` del contrato.
- **R9.3** El esqueleto deberá hacer que los modelos de cada capa se creen exactamente en los schemas `staging` y `marts`, sin prefijos añadidos por dbt.
- **R9.4** El esqueleto deberá incluir un único modelo de ejemplo con sus pruebas, marcado como ejemplo que B puede conservar o reemplazar.
- **R9.5** Cuando se ejecuten `dbt debug`, `dbt run` y `dbt test` sobre el esqueleto con `raw` cargado, los tres deberán terminar sin errores.
- **R9.6** El esqueleto no deberá definir el modelo dimensional ni modelos de `marts`.

### R10 — Independencia entre roles

- **R10.1** Las pruebas automáticas del DAG no deberán depender del contenido del proyecto dbt real.
- **R10.2** Cuando B agregue, cambie o elimine modelos, pruebas o validaciones, el DAG deberá ejecutarlos sin cambios en archivos del rol A.
- **R10.3** El repositorio deberá incluir una guía para B con el arranque del entorno, la carga de `raw`, la ejecución de dbt, las convenciones y los límites de la interfaz.

## Criterios de aceptación (Gherkin)

```gherkin
Característica: Orquestación del pipeline

  Escenario: El DAG se carga sin errores
    Dado el entorno en ejecución
    Cuando consulto los errores de importación de Airflow
    Entonces no hay ninguno
    Y existe el DAG "sgfood_elt" en pausa

  Escenario: Estructura del DAG
    Cuando inspecciono las tareas de "sgfood_elt"
    Entonces hay una tarea de carga por cada fuente de "fuentes.yml"
    Y "validar_carga_raw" depende de todas las tareas de carga
    Y "dbt_deps" depende de "validar_carga_raw"
    Y "dbt_run" depende de "dbt_deps"
    Y "dbt_test" depende de "dbt_run"
    Y "validar_marts" depende de "dbt_test"

  Escenario: Ejecución completa exitosa
    Dado el entorno en ejecución con un proyecto dbt válido
    Cuando disparo "sgfood_elt" y espero a que termine
    Entonces la ejecución termina en "success"
    Y todas las tareas terminan en "success"
    Y raw contiene 8864 filas con un único valor de "_loaded_at"
    Y los modelos del proyecto dbt existen en el DW

  Escenario: dbt run falla
    Dado un proyecto dbt con un modelo que no compila
    Cuando disparo "sgfood_elt" con ese proyecto
    Entonces "dbt_run" termina en "failed"
    Y "dbt_test" y "validar_marts" no se ejecutan
    Y la ejecución termina en "failed"
    Y raw conserva sus 8864 filas

  Escenario: Una prueba dbt falla
    Dado un proyecto dbt con una prueba que no se cumple
    Cuando disparo "sgfood_elt" con ese proyecto
    Entonces "dbt_run" termina en "success"
    Y "dbt_test" termina en "failed"
    Y "validar_marts" no se ejecuta

  Escenario: Una validación final falla
    Dado una carpeta de validaciones con una consulta que devuelve filas
    Cuando disparo "sgfood_elt" con esa carpeta
    Entonces "validar_marts" termina en "failed"
    Y su registro nombra el archivo y muestra las filas devueltas

  Escenario: Sin validaciones finales
    Dado una carpeta de validaciones vacía
    Cuando disparo "sgfood_elt"
    Entonces "validar_marts" termina en "success"
    Y su registro contiene una advertencia de que no había validaciones

  Escenario: Sin ejecuciones simultáneas
    Dado una ejecución de "sgfood_elt" en curso
    Cuando disparo otra ejecución
    Entonces la segunda no inicia sus tareas hasta que termina la primera

  Escenario: Esqueleto dbt ejecutable
    Dado el entorno en ejecución con raw cargado
    Cuando ejecuto "dbt debug", "dbt run" y "dbt test" sobre "dbt_project"
    Entonces los tres terminan sin errores
    Y el modelo de ejemplo existe en el schema "staging"
    Y no existe ningún schema con prefijo añadido por dbt

  Escenario: Pipeline completo con el proyecto real
    Dado el entorno en ejecución con el esqueleto dbt
    Cuando disparo "sgfood_elt" con los parámetros predeterminados
    Entonces todas las tareas terminan en "success"

  Escenario: B agrega un modelo sin tocar el DAG
    Dado el esqueleto dbt
    Cuando agrego un modelo nuevo al proyecto y disparo "sgfood_elt"
    Entonces el modelo nuevo se crea en el DW
    Y ningún archivo del rol A cambió

  Escenario: Levantar el entorno no dispara el pipeline
    Dado un entorno recién iniciado
    Cuando pasan dos ciclos del scheduler
    Entonces "sgfood_elt" no tiene ejecuciones
```

## Dependencias con el rol B (zona amarilla)

Esta feature toca dos temas compartidos del steering: la tarea que ejecuta dbt y la tarea de validaciones. B todavía no comenzó y pidió una base para arrancar, así que A definió estos puntos el 2026-10-10 como punto de partida (decisiones D9, D10 y D11). B puede cambiarlos después por el procedimiento normal de zona amarilla.

| Tema | Propuesta | Detalle en |
|------|-----------|-----------|
| Comandos de dbt | `dbt run` y `dbt test` sobre el proyecto completo, sin selectores | [design.md](design.md) |
| `dbt deps` | Se ejecuta antes de `dbt run` solo si el proyecto tiene `packages.yml` | [design.md](design.md) |
| Ubicación de `profiles.yml` | Dentro de `dbt_project/`, leyendo `DW_HOST`, `DW_PORT`, `DW_DB`, `DW_USER` y `DW_PASSWORD` | [design.md](design.md) |
| Carpeta de validaciones finales | `Proyecto1/sql/validaciones/dag/` | [design.md](design.md) |
| Convención de las validaciones | Una consulta por archivo `.sql`; pasa si devuelve cero filas | [design.md](design.md) |
| Montaje de `sql/` en los contenedores | Solo lectura en `/opt/airflow/sql` | [design.md](design.md) |

**Dos proyectos dbt, dos propósitos.** Las pruebas automáticas del DAG usan proyectos mínimos de prueba, para no depender de lo que B haga con el proyecto real. El proyecto real nace como esqueleto en esta feature, se usa para la ejecución de evidencia y pasa a ser propiedad de B al entregarse.

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| El esqueleto condiciona decisiones de diseño que son de B | Contiene solo configuración, fuentes y un modelo de ejemplo; no define hechos, dimensiones ni `marts` |
| Un cambio de B en el proyecto real rompe las pruebas de A | Las pruebas del DAG usan sus propios proyectos de prueba |
| dbt agrega un prefijo al nombre de los schemas y crea `staging_staging` | El esqueleto fija el nombre exacto del schema y una prueba lo comprueba |
| La API de Airflow 3 difiere de los ejemplos habituales de Airflow 2 | Verificar importaciones y parámetros contra la documentación de la versión 3.3.2 antes de escribir |
| Dos ejecuciones simultáneas truncan y recargan a la vez | Una sola ejecución activa por DAG |
| El DAG de prueba de `entorno-base` y la prueba de lista de DAGs vacía chocan con el DAG real | Se ajustan en esta feature |
| Leer `fuentes.yml` al analizar el DAG lo vuelve lento o frágil | Es un archivo pequeño; un error de configuración debe aparecer como error de importación visible |
| Las pruebas dejan objetos de prueba en el DW | El proyecto dbt de prueba escribe en un schema propio que se elimina al terminar |
