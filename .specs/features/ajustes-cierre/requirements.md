# Requisitos — `ajustes-cierre`

Corrige los defectos encontrados en la revisión del trabajo del rol B y alinea código, pruebas y documentos para dejar el Proyecto 1 listo para entregar. B autorizó el 2026-10-14 que el rol A aplique los cambios directamente en su zona; al terminar se le informa lo hecho.

- **Rol que ejecuta:** A, con autorización de B para editar `dbt_project/` y `sql/validaciones/` (decisión D12).
- **Steering:** [architecture.md](../../steering/architecture.md) · [tech-stack.md](../../steering/tech-stack.md) · [coding-standards.md](../../steering/coding-standards.md)
- **Origen:** revisión del commit `5c50f47` del rol B, registrada en Engram bajo `review/rol-b`.
- **Siguientes documentos:** [design.md](design.md) · [tasks.md](tasks.md)

## Problema

El pipeline completo corre en verde con el proyecto de B, pero la revisión encontró:

| # | Hallazgo | Severidad | Zona |
|---|----------|-----------|------|
| H1 | Las dimensiones numeran sus claves con `ROW_NUMBER()` y el hecho incremental `fct_ventas_linea` solo inserta: un cambio en la fuente deja ventas apuntando a otro cliente, sin que ninguna prueba lo detecte | Alta | B |
| H2 | Las consultas de ingresos suman ventas `ANULADA` (48) y `PENDIENTE` (23) | Media | B |
| H3 | Conversiones de tipo que detienen `dbt run` ante una fecha imposible o un decimal fuera de rango | Media | B |
| H4 | Faltan pruebas de relaciones, de valores aceptados en `marts` y de `not_null` en columnas que lo requieren | Media | B |
| H5 | `int_ventas_linea` descarta en silencio las líneas sin venta (`INNER JOIN`) | Media | B |
| H6 | El enunciado pide un DDL con hechos, dimensiones, relaciones y claves; solo existe el de `raw` y `marts` no tiene claves físicas | Media | B |
| H7 | Ninguna columna de `marts` tiene descripción; el estándar lo exige | Media | B |
| H8 | README y `dbt_project/README.md` con afirmaciones falsas o desactualizadas | Baja | B |
| H9 | Las validaciones finales no cubren todos los hechos y una de ellas no puede detectar negativos | Baja | B |
| H10 | `docker-compose.yml` con un servicio pgAdmin sin versión fija, con contraseña literal, correo personal y volúmenes mal montados | Media | A |
| H11 | Una prueba del rol A exige que el proyecto dbt tenga un solo modelo | Baja | A |
| H12 | La guía de B y el steering no reflejan lo que B decidió e hizo | Baja | A |
| H13 | No está registrado qué se decidió sobre los casos de calidad opcionales | Baja | Ambos |
| H14 | La evidencia de dbt se generó a mano, no desde una ejecución del DAG | Baja | B |

## Casos de uso

| ID | Actor | Caso de uso | Resultado |
|----|-------|-------------|-----------|
| CU1 | Evaluador | Revisar el modelo dimensional | Claves estables, relaciones físicas y documentadas, DDL disponible |
| CU2 | Evaluador | Ejecutar el pipeline desde un clon limpio | Las 17 tareas en verde y los `marts` correctos |
| CU3 | Cualquier integrante | Volver a ejecutar el pipeline tras un cambio en la fuente | Los hechos reflejan el cambio y apuntan a las dimensiones correctas |
| CU4 | Evaluador | Leer las cifras de negocio | Los ingresos consideran solo ventas completadas |
| CU5 | Evaluador | Comprobar la calidad de datos | Las pruebas dbt detectan los casos inválidos de `casos_calidad_opcionales.csv` |
| CU6 | Rol B | Retomar el proyecto | Sabe qué cambió y por qué |

## Alcance

**Incluye:** los hallazgos H1 a H14.

**No incluye:**

| Fuera de alcance | Motivo |
|------------------|--------|
| Rediseñar el modelo dimensional (hechos, dimensiones o granos) | El diseño de B es correcto; solo se corrigen claves, pruebas y documentación |
| Cambios a la ingesta, al contrato raw o al DAG | Están verificados y no tienen hallazgos |
| Herramienta de visualización | Opcional y no solicitada |
| Reescribir la historia de git | Decisión ya tomada |

## Requisitos (EARS)

### R1 — Claves estables (H1)

- **R1.1** Cada dimensión deberá generar su clave sustituta de forma determinista a partir de su clave natural, de modo que la misma entidad reciba la misma clave en todas las ejecuciones.
- **R1.2** Cuando una fila de la fuente cambie, el hecho incremental deberá actualizar la fila correspondiente en lugar de conservar la versión anterior.
- **R1.3** El hecho incremental deberá seguir materializado como `incremental`.
- **R1.4** Cuando se ejecute el pipeline dos veces sin cambios en la fuente, cada hecho deberá contener exactamente las mismas filas y claves.

### R2 — Reglas de negocio en las consultas (H2)

- **R2.1** Las consultas de ingresos y de cumplimiento de metas deberán considerar solo las ventas con estado `COMPLETADA`.
- **R2.2** El README deberá declarar esa regla y mostrar por separado las ventas anuladas y pendientes.

### R3 — Conversiones tolerantes (H3)

- **R3.1** Toda conversión de `TEXT` a entero, decimal o fecha en `staging` deberá devolver `NULL` ante un valor inválido, en lugar de detener `dbt run`.
- **R3.2** Las conversiones deberán realizarse con un único macro reutilizable.
- **R3.3** Cuando un valor no pueda convertirse en una columna obligatoria, una prueba dbt deberá fallar.

### R4 — Cobertura de pruebas (H4, H5)

- **R4.1** Toda clave sustituta de `marts` deberá tener pruebas `unique` y `not_null`.
- **R4.2** Toda clave foránea de un hecho y de `dim_promocion` deberá tener una prueba `relationships`.
- **R4.3** Las columnas categóricas de `marts` deberán tener pruebas `accepted_values` con los valores reales de la fuente.
- **R4.4** Las columnas que la fuente declara obligatorias deberán tener `not_null` en `staging`.
- **R4.5** `int_ventas_linea` no deberá descartar líneas sin venta; una prueba de relación en `staging` deberá reportarlas.

### R5 — Claves físicas y DDL (H6)

- **R5.1** Cada tabla de `marts` deberá tener una clave primaria física.
- **R5.2** Cada clave foránea de los hechos deberá existir como restricción física hacia su dimensión.
- **R5.3** Las restricciones deberán sobrevivir a ejecuciones sucesivas del pipeline, incluido el hecho incremental.
- **R5.4** El repositorio deberá incluir un script DDL de referencia del schema `marts`, extraído de la base después de una ejecución real, con tablas, claves primarias y foráneas.

### R6 — Documentación (H7, H8, H12, H13)

- **R6.1** Cada modelo y cada columna de `marts` deberá tener descripción en YAML.
- **R6.2** El README y `dbt_project/README.md` no deberán contener afirmaciones que contradigan el código o la evidencia.
- **R6.3** La guía de B y el steering deberán reflejar las decisiones tomadas por B y por esta feature.
- **R6.4** La decisión sobre los casos de calidad opcionales deberá quedar registrada.

### R7 — Validaciones finales (H9)

- **R7.1** Las validaciones de `sql/validaciones/dag/` deberán cubrir la integridad referencial de los cinco hechos.
- **R7.2** Ninguna validación deberá contener condiciones que no puedan cumplirse con los datos de `staging`.

### R8 — Entorno (H10, H11)

- **R8.1** El servicio pgAdmin deberá usar una imagen con versión fija, credenciales tomadas de `.env` y un único volumen para sus datos.
- **R8.2** pgAdmin no deberá iniciarse con `docker compose up` sin indicarlo de forma explícita.
- **R8.3** Las pruebas del rol A deberán pasar con el proyecto dbt completo y no depender de su contenido.

### R9 — Casos de calidad (H13)

- **R9.1** El sistema deberá permitir cargar los casos de `casos_calidad_opcionales.csv` sobre una copia de los datos y ejecutar las pruebas dbt contra ellos, sin afectar la corrida principal.
- **R9.2** Las pruebas dbt deberán detectar cada caso que corresponda a una tabla cargada en `raw`.

### R10 — Evidencia (H14)

- **R10.1** La evidencia de dbt deberá provenir de una ejecución del DAG desde un entorno limpio.
- **R10.2** Toda cifra del README deberá coincidir con un archivo de evidencia.

## Criterios de aceptación (Gherkin)

```gherkin
Característica: Ajustes de cierre

  Escenario: Claves estables entre ejecuciones
    Dado una ejecución completa del pipeline
    Cuando ejecuto el pipeline otra vez sin cambios en la fuente
    Entonces cada clave sustituta de cada dimensión conserva su valor
    Y cada hecho tiene las mismas filas que en la ejecución anterior

  Escenario: Un cambio en la fuente se refleja en el hecho
    Dado una ejecución completa del pipeline
    Y una venta que cambia de estado "PENDIENTE" a "ANULADA" en la base fuente
    Cuando ejecuto el pipeline otra vez
    Entonces sus líneas en "fct_ventas_linea" tienen estado "ANULADA"
    Y "fct_ventas_linea" conserva 3209 filas

  Escenario: Una entidad nueva no reasigna claves
    Dado una ejecución completa del pipeline
    Cuando agrego en la base fuente un cliente con identificador 0 y ejecuto el pipeline
    Entonces la clave de cada uno de los 250 clientes existentes no cambió
    Y cada línea de "fct_ventas_linea" apunta al mismo cliente que antes

  Escenario: Ingresos solo de ventas completadas
    Cuando ejecuto la consulta de ventas por sucursal
    Entonces el total coincide con la suma de subtotales de ventas con estado "COMPLETADA"

  Escenario: Fecha imposible no detiene dbt
    Dado un valor "2026-02-30" en una columna de fecha de raw
    Cuando ejecuto "dbt run"
    Entonces termina sin errores
    Y el valor queda en NULL
    Y "dbt test" reporta la falla en la columna obligatoria

  Escenario: Claves físicas presentes
    Dado una ejecución completa del pipeline
    Cuando consulto las restricciones del schema "marts"
    Entonces cada tabla tiene clave primaria
    Y cada clave foránea de cada hecho existe como restricción
    Y siguen existiendo después de una segunda ejecución

  Escenario: Casos de calidad detectados
    Dado los casos de "casos_calidad_opcionales.csv" cargados sobre una copia de raw
    Cuando ejecuto "dbt test" contra esa copia
    Entonces cada caso correspondiente a una tabla de raw produce al menos una prueba fallida
    Y la corrida principal no se ve afectada

  Escenario: Pipeline limpio de punta a punta
    Dado un entorno sin contenedores ni volúmenes previos
    Cuando levanto el entorno, ejecuto el DAG y espero a que termine
    Entonces las 17 tareas terminan en "success"
    Y todas las pruebas automáticas del repositorio pasan

  Escenario: pgAdmin opcional y sin secretos
    Cuando reviso "docker-compose.yml"
    Entonces ninguna imagen usa "latest" ni omite su versión
    Y ninguna credencial es literal
    Y "docker compose up -d" no inicia pgAdmin
```

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| Las restricciones físicas impiden reconstruir una dimensión que un hecho referencia | Las claves foráneas se crean después de construir cada hecho y se recrean en cada ejecución; se prueba con dos ejecuciones seguidas |
| Cambiar las claves de entero a texto rompe consultas existentes | Se actualizan las consultas de `sql/validaciones/` y se ejecutan todas |
| Los escenarios que modifican la base fuente dejan datos alterados | Cada prueba restaura la fuente al terminar; se verifica con los conteos del contrato |
| La función de validación de tipos depende de la versión de PostgreSQL | Se confirma contra la documentación de PostgreSQL 16 antes de usarla |
| B retoma el proyecto sin conocer los cambios | Descripción del pull request con la lista de cambios y motivo de cada uno |
