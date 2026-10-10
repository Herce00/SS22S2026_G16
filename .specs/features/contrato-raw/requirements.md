# Requisitos — `contrato-raw`

Define y materializa la interfaz entre ingesta y transformación: qué tablas y columnas tendrá `raw`, de qué fuente sale cada una y cómo llegan los valores. Deja además la base fuente poblada con los datos oficiales. Al terminar, B puede escribir `sources.yml` y `staging`, y A puede construir la carga.

- **Rol dueño:** A (ingesta y orquestación). El contrato es compartido: A propone, B valida.
- **Steering:** [architecture.md](../../steering/architecture.md) · [tech-stack.md](../../steering/tech-stack.md) · [coding-standards.md](../../steering/coding-standards.md)
- **Feature anterior:** [entorno-base](../entorno-base/requirements.md)
- **Siguientes documentos:** [design.md](design.md) · [tasks.md](tasks.md)

## Problema

Los datos oficiales ya están en `Proyecto1/data/`, pero la base fuente está vacía, `raw` no tiene tablas y no existe un documento que diga a B qué va a encontrar. Sin eso, ninguno de los dos puede avanzar sin suponer nombres.

## Casos de uso

| ID | Actor | Caso de uso | Resultado |
|----|-------|-------------|-----------|
| CU1 | Rol B | Consultar el contrato para escribir `sources.yml` y `staging` | Conoce tablas, columnas, tipo esperado y reglas de cada campo |
| CU2 | Rol A | Leer la configuración de fuentes desde el código de carga | Obtiene origen, destino y columnas de cada tabla sin nombres escritos a mano |
| CU3 | Cualquier integrante | Levantar el entorno desde cero | La base fuente queda poblada y `raw` tiene sus 12 tablas vacías |
| CU4 | Cualquier integrante | Cambiar una tabla o columna de `raw` | Las pruebas fallan si contrato, configuración y DDL dejan de coincidir |
| CU5 | Rol B | Validar conteos de punta a punta | Dispone de la cantidad de filas esperada por fuente |

## Alcance

**Incluye:**

- Versionar los datos oficiales de `Proyecto1/data/` sin alterarlos.
- Cargar `sgfood_oltp.sql` en la base fuente al inicializarla.
- Archivo de configuración de fuentes (decisión D1), que es la versión legible por máquina del contrato.
- DDL de las 12 tablas de `raw`.
- Documento `Proyecto1/docs/contrato_raw.md` versión `v1`.
- Pruebas de consistencia entre datos, configuración, DDL y documento.

**No incluye:**

| Fuera de alcance | Dónde va |
|------------------|----------|
| Código Python de extracción y carga | Feature `ingesta-raw` |
| DAG de Airflow | Feature `dag-orquestacion` |
| `sources.yml`, modelos y pruebas dbt | Rol B |
| Carga o uso de `casos_calidad_opcionales.csv` | Decisión D8: opcional, lo define B |
| Conversión de tipos o reglas de negocio | Modelos `staging` de B |

## Requisitos (EARS)

### R1 — Datos oficiales versionados

- **R1.1** El repositorio deberá contener los archivos oficiales de `Proyecto1/data/` con el mismo contenido byte a byte con que fueron entregados.
- **R1.2** El sistema de control de versiones no deberá convertir los fines de línea ni la codificación de esos archivos.

### R2 — Base fuente poblada

- **R2.1** Cuando la base fuente se inicialice por primera vez, el sistema deberá ejecutar `sgfood_oltp.sql` y crear el schema `oltp_sgfood` con sus 7 tablas.
- **R2.2** Cuando la inicialización termine, cada tabla de `oltp_sgfood` deberá contener la cantidad de filas indicada en el contrato.
- **R2.3** El sistema no deberá modificar `sgfood_oltp.sql` para cargarlo.

### R3 — Configuración de fuentes

- **R3.1** El sistema deberá declarar en un único archivo cada tabla de `raw` con su tipo de fuente, su origen y su lista ordenada de columnas.
- **R3.2** El archivo deberá declarar exactamente 12 tablas: 7 de la base transaccional y 5 de archivos CSV.
- **R3.3** Las columnas declaradas para cada fuente CSV deberán coincidir, en nombre y orden, con el encabezado del archivo leído como `utf-8-sig`.
- **R3.4** Las columnas declaradas para cada fuente transaccional deberán coincidir, en nombre y orden, con las de la tabla en `oltp_sgfood`.
- **R3.5** El archivo no deberá declarar `casos_calidad_opcionales.csv` como fuente.

### R4 — Tablas de `raw`

- **R4.1** Cuando el DW se inicialice por primera vez, el sistema deberá crear en `raw` una tabla por cada fuente declarada.
- **R4.2** Cada tabla de `raw` deberá tener las columnas de negocio declaradas, todas de tipo `TEXT`, seguidas de `_loaded_at` y `_source`.
- **R4.3** Las tablas de `raw` no deberán tener claves primarias, claves foráneas ni restricciones sobre columnas de negocio.
- **R4.4** El script DDL deberá poder ejecutarse más de una vez sin errores ni cambios.
- **R4.5** Al terminar esta feature, las tablas de `raw` deberán existir vacías.

### R5 — Documento de contrato

- **R5.1** El contrato deberá listar cada tabla de `raw` con su fuente, su granularidad y su cantidad de filas esperada.
- **R5.2** El contrato deberá listar cada columna con el tipo esperado y la clave o regla que indica el diccionario oficial.
- **R5.3** El contrato deberá definir cómo se representan en `raw` los valores nulos, las fechas, los números y los booleanos.
- **R5.4** El contrato deberá indicar su versión y el procedimiento para cambiarlo.

### R6 — Consistencia verificable

- **R6.1** Si la configuración de fuentes, el DDL y el documento de contrato dejan de coincidir en tablas o columnas, entonces las pruebas automáticas deberán fallar.

## Criterios de aceptación (Gherkin)

```gherkin
Característica: Contrato raw

  Escenario: Base fuente poblada desde cero
    Dado un entorno sin contenedores ni volúmenes previos
    Cuando ejecuto "docker compose up -d" en Proyecto1
    Entonces la base fuente tiene el schema "oltp_sgfood" con 7 tablas
    Y las tablas contienen 6, 8, 10, 80, 250, 1200 y 3209 filas
      para sucursal, categoria, marca, producto, cliente, venta y venta_detalle

  Escenario: Tablas raw creadas y vacías
    Dado el entorno en ejecución
    Cuando consulto las tablas del schema "raw" del DW
    Entonces existen exactamente las 12 tablas declaradas en la configuración de fuentes
    Y todas están vacías
    Y los schemas "staging" y "marts" no contienen tablas

  Escenario: Columnas de raw según el contrato
    Dado el entorno en ejecución
    Cuando consulto las columnas de cada tabla de "raw"
    Entonces las columnas de negocio coinciden en nombre y orden con la configuración de fuentes
    Y todas las columnas de negocio son de tipo "text"
    Y cada tabla termina con las columnas "_loaded_at" y "_source"

  Escenario: Configuración alineada con los CSV
    Cuando leo el encabezado de cada archivo CSV como "utf-8-sig"
    Entonces coincide en nombre y orden con las columnas declaradas para esa fuente

  Escenario: Configuración alineada con la base fuente
    Dado el entorno en ejecución
    Cuando consulto las columnas de cada tabla de "oltp_sgfood"
    Entonces coinciden en nombre y orden con las columnas declaradas para esa fuente

  Escenario: Documento alineado con la configuración
    Cuando comparo el documento de contrato con la configuración de fuentes
    Entonces el documento menciona cada tabla y cada columna declarada
    Y no menciona tablas que la configuración no declara

  Escenario: Casos de calidad fuera de la corrida principal
    Cuando reviso la configuración de fuentes
    Entonces "casos_calidad_opcionales.csv" no aparece como fuente

  Escenario: DDL reejecutable
    Dado el entorno en ejecución
    Cuando ejecuto el script DDL de tablas raw por segunda vez con detención ante errores
    Entonces termina sin errores
```

## Dependencias con el rol B (zona amarilla)

Todo el contenido del contrato es compartido. La pareja aceptó estos seis puntos sin cambios el 2026-10-09; modificarlos después sigue el procedimiento de cambio del contrato.

| Tema | Propuesta | Detalle en |
|------|-----------|-----------|
| Nombres de tablas `raw` | Iguales a la fuente, sin prefijo | [design.md](design.md) |
| Nombres de columnas | Iguales a la fuente | [design.md](design.md) |
| Representación de nulos | Campo CSV vacío se carga como `NULL` | [design.md](design.md) |
| Representación de booleanos | Texto `true` / `false` | [design.md](design.md) |
| Columnas de auditoría | `_loaded_at` y `_source` al final de cada tabla | [design.md](design.md) |
| Casos de calidad opcionales | No se cargan (decisión D8) | [architecture.md](../../steering/architecture.md) |

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| Git altera los CSV (fin de línea o BOM) y cambian los conteos | Regla en `.gitattributes` y prueba que verifica el contenido |
| `sgfood_oltp.sql` empieza con `DROP SCHEMA ... CASCADE` | Solo se ejecuta al inicializar un volumen vacío; no se aplica a mano sobre datos existentes |
| Volúmenes ya creados no ejecutan los nuevos scripts de inicialización | Documentar el reinicio con `down -v` o la aplicación manual |
| La prueba de `entorno-base` que exige `raw` sin tablas deja de ser válida | Se actualiza en esta feature |
| El contrato se desalinea con el tiempo | Pruebas de consistencia (R6) |
