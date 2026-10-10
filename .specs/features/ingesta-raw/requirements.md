# Requisitos — `ingesta-raw`

Paquete Python que lee la configuración de fuentes, extrae de la base transaccional y de los CSV, y carga las 12 tablas de `raw` respetando el contrato. Al terminar, `raw` contiene los datos oficiales y B puede ejecutar dbt sobre datos reales.

- **Rol dueño:** A (ingesta y orquestación)
- **Steering:** [architecture.md](../../steering/architecture.md) · [tech-stack.md](../../steering/tech-stack.md) · [coding-standards.md](../../steering/coding-standards.md)
- **Feature anterior:** [contrato-raw](../contrato-raw/requirements.md)
- **Contrato que implementa:** `Proyecto1/docs/contrato_raw.md` versión 1
- **Siguientes documentos:** [design.md](design.md) · [tasks.md](tasks.md)

## Problema

Las 12 tablas de `raw` existen pero están vacías. Falta el proceso de extracción y carga con Python que exige el enunciado, y sin datos en `raw` B solo puede desarrollar a ciegas.

## Casos de uso

| ID | Actor | Caso de uso | Resultado |
|----|-------|-------------|-----------|
| CU1 | Rol A | Cargar todas las fuentes con un comando | Las 12 tablas de `raw` quedan con los datos oficiales |
| CU2 | Rol A | Cargar una sola tabla | Solo esa tabla se recarga; las demás no cambian |
| CU3 | Tarea de Airflow (feature siguiente) | Invocar la carga de una tabla como función | Recibe un resultado con filas leídas y cargadas, o una excepción |
| CU4 | Cualquier integrante | Reejecutar la carga | `raw` queda igual, sin filas duplicadas |
| CU5 | Rol A | Diagnosticar una carga fallida | El registro indica fuente, tabla y causa; la tabla conserva sus datos anteriores |
| CU6 | Rol B | Ejecutar dbt sobre `raw` | Encuentra los valores con el formato que promete el contrato |

## Alcance

**Incluye:**

- Paquete Python de ingesta, ejecutable por línea de comandos y como función.
- Extracción desde `oltp_sgfood` y desde los cinco CSV.
- Limpieza técnica mínima definida en el contrato.
- Carga a `raw` por truncado y recarga dentro de una transacción.
- Verificación de filas cargadas contra filas leídas.
- Pruebas unitarias y de integración.
- Evidencia de una carga completa real.

**No incluye:**

| Fuera de alcance | Dónde va |
|------------------|----------|
| DAG, tareas, reintentos y programación | Feature `dag-orquestacion` |
| Validaciones de conteo fuente contra `marts` | Feature `dag-orquestacion` |
| Conversión de tipos, deduplicación, reglas de negocio | Modelos dbt de B |
| Carga de `casos_calidad_opcionales.csv` | Decisión D8 |
| Cambios al contrato raw | Procedimiento de cambio del contrato |

## Requisitos (EARS)

### R1 — Guiado por configuración

- **R1.1** El sistema deberá obtener de `fuentes.yml` la lista de tablas, su tipo, su origen y sus columnas.
- **R1.2** El código no deberá contener nombres de tablas ni de columnas de negocio escritos a mano.
- **R1.3** Si `fuentes.yml` no existe o no cumple su estructura, entonces el sistema deberá fallar antes de abrir conexiones, indicando el problema.

### R2 — Extracción desde la base transaccional

- **R2.1** Cuando se cargue una fuente de tipo `postgres`, el sistema deberá leer todas las filas de la tabla de origen con las columnas declaradas, en el orden declarado.
- **R2.2** El sistema deberá convertir cada columna a texto en la consulta de extracción.
- **R2.3** El sistema deberá construir la consulta con identificadores escapados, sin concatenar texto.
- **R2.4** El sistema no deberá modificar datos en la base transaccional.

### R3 — Extracción desde CSV

- **R3.1** Cuando se cargue una fuente de tipo `csv`, el sistema deberá leer el archivo con codificación `utf-8-sig`, sin inferir tipos.
- **R3.2** Si el encabezado del archivo no coincide en nombre y orden con las columnas declaradas, entonces el sistema deberá fallar sin cargar ninguna fila.
- **R3.3** Si una fila tiene una cantidad de campos distinta a la del encabezado, entonces el sistema deberá fallar indicando el número de línea.
- **R3.4** El sistema deberá omitir las líneas completamente vacías.
- **R3.5** El sistema deberá cargar los campos vacíos como `NULL`.
- **R3.6** El sistema no deberá recortar espacios, cambiar mayúsculas ni alterar de otro modo los valores.

### R4 — Carga a `raw`

- **R4.1** El sistema deberá truncar y recargar cada tabla dentro de una única transacción.
- **R4.2** Si la carga de una tabla falla, entonces la tabla deberá conservar los datos que tenía antes.
- **R4.3** El sistema deberá asignar a `_source` el origen declarado en la configuración.
- **R4.4** El sistema deberá asignar a `_loaded_at` el mismo instante a todas las filas cargadas en una misma ejecución.
- **R4.5** Cuando la carga de una tabla termine, el sistema deberá comprobar que las filas en `raw` son tantas como las leídas de la fuente.
- **R4.6** Si las cantidades no coinciden, entonces el sistema deberá revertir la carga y fallar.
- **R4.7** El sistema deberá escribir únicamente en el schema `raw`.

### R5 — Idempotencia

- **R5.1** Cuando la carga se ejecute más de una vez sobre las mismas fuentes, cada tabla de `raw` deberá contener las mismas filas de negocio que tras la primera ejecución.

### R6 — Fidelidad al contrato

- **R6.1** Tras una carga completa, cada tabla de `raw` deberá contener la cantidad de filas indicada en el contrato.
- **R6.2** Los valores de `raw` deberán cumplir las reglas de representación del contrato para nulos, enteros, decimales, fechas y booleanos.
- **R6.3** El contenido de negocio de cada tabla de `raw` deberá ser igual al de su fuente convertido a texto.

### R7 — Ejecución

- **R7.1** El sistema deberá poder ejecutarse por línea de comandos para todas las tablas o para una tabla indicada.
- **R7.2** El sistema deberá exponer una función que cargue una tabla y devuelva las filas leídas, las filas cargadas y la duración.
- **R7.3** Si se indica una tabla que no está en la configuración, entonces el sistema deberá fallar listando las tablas válidas.
- **R7.4** Cuando la ejecución por línea de comandos falle, el proceso deberá terminar con un código distinto de cero.
- **R7.5** El sistema deberá poder ejecutarse fuera de Airflow.

### R8 — Configuración y registro

- **R8.1** El sistema deberá leer los parámetros de conexión desde las variables de entorno definidas en `entorno-base`.
- **R8.2** El sistema no deberá escribir contraseñas en el registro.
- **R8.3** El sistema deberá registrar, por cada tabla, el origen, el destino, las filas leídas, las filas cargadas y la duración.
- **R8.4** Si ocurre un error, entonces el sistema deberá registrarlo y propagarlo, sin silenciarlo.

## Criterios de aceptación (Gherkin)

```gherkin
Característica: Ingesta a raw

  Escenario: Carga completa
    Dado el entorno en ejecución con las tablas de raw vacías
    Cuando ejecuto la carga de todas las fuentes
    Entonces el proceso termina con código 0
    Y cada tabla de raw tiene la cantidad de filas indicada en el contrato
    Y raw contiene 8864 filas en total

  Escenario: Carga de una sola tabla
    Dado una carga completa previa
    Cuando ejecuto la carga solo de "devoluciones"
    Entonces "devoluciones" tiene 80 filas con un "_loaded_at" más reciente
    Y el "_loaded_at" de las demás tablas no cambió

  Escenario: Reejecución sin duplicados
    Dado una carga completa previa
    Cuando ejecuto la carga de todas las fuentes otra vez
    Entonces cada tabla de raw tiene la misma cantidad de filas
    Y el contenido de negocio de cada tabla es idéntico

  Escenario: Contenido fiel a la base transaccional
    Dado una carga completa
    Cuando comparo cada tabla de "oltp_sgfood" convertida a texto con su tabla en raw
    Entonces no hay filas de diferencia en ningún sentido

  Escenario: Contenido fiel a los CSV
    Dado una carga completa
    Cuando comparo cada archivo CSV con su tabla en raw
    Entonces cada fila del archivo aparece en raw con los mismos valores

  Escenario: Representación de valores
    Dado una carga completa
    Entonces "producto.activo" solo contiene "true" o "false"
    Y "venta_detalle.descuento" tiene siempre cuatro decimales
    Y "venta.fecha" tiene siempre el formato "YYYY-MM-DD"
    Y los nulos de "cliente.municipio" en raw son tantos como en la fuente
    Y ninguna columna de negocio contiene cadenas vacías

  Escenario: Columnas de auditoría
    Dado una carga completa
    Entonces "_source" de cada tabla es igual al origen declarado en la configuración
    Y todas las filas cargadas en esa ejecución comparten el mismo "_loaded_at"

  Escenario: Encabezado de CSV incorrecto
    Dado una carga completa previa
    Y un archivo "promociones.csv" cuyo encabezado no coincide con la configuración
    Cuando ejecuto la carga de "promociones"
    Entonces el proceso termina con código distinto de 0
    Y "promociones" conserva sus 30 filas anteriores

  Escenario: Fila con cantidad de campos incorrecta
    Dado una carga completa previa
    Y un archivo "promociones.csv" con una fila a la que le falta un campo
    Cuando ejecuto la carga de "promociones"
    Entonces el proceso termina con código distinto de 0 indicando el número de línea
    Y "promociones" conserva sus 30 filas anteriores

  Escenario: Tabla desconocida
    Cuando ejecuto la carga de "tabla_inexistente"
    Entonces el proceso termina con código distinto de 0
    Y el mensaje lista las tablas válidas

  Escenario: Sin escritura fuera de raw
    Dado una carga completa
    Entonces los schemas "staging" y "marts" no contienen tablas creadas por la ingesta
    Y los conteos de "oltp_sgfood" no cambiaron
```

## Dependencias con el rol B

Esta feature implementa el contrato ya validado y no lo modifica. No abre temas de zona amarilla nuevos, salvo estos avisos:

| Tema | Detalle |
|------|---------|
| Punto de integración 3 | Al terminar, `raw` tiene datos reales; B puede pasar de datos supuestos a `dbt run` real |
| Variable `PYTHONPATH` en los contenedores de Airflow | Se agrega `/opt/airflow/python`; no afecta a dbt, que corre en su propio entorno virtual |
| Prueba de `contrato-raw` que exige `raw` vacío | Deja de ser válida y se retira en esta feature |

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| La base fuente se reporta sana antes de terminar su script de inicialización | El healthcheck de `src` pasa a comprobar que los datos existen |
| Diferencias de formato entre el driver y PostgreSQL al convertir a texto | La conversión se hace en la consulta, no en Python |
| Una librería infiere tipos o convierte vacíos en `NaN` | Lectura con el módulo `csv` de la biblioteca estándar, todo como texto |
| Carga parcial ante un fallo | Una transacción por tabla y verificación de conteo antes de confirmar |
| Las pruebas dejan `raw` en un estado distinto al esperado por otras pruebas | Cada prueba de integración prepara el estado que necesita |
