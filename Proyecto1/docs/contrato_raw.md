# Contrato de Datos de la Capa Raw (SG-Food) — Versión 1

Este documento formaliza el contrato de interfaz entre la ingesta técnica (Rol A) y la transformación dimensional con dbt (Rol B) para el Proyecto 1 (SG-Food).
Define la estructura, tipos esperados, granularidad, reglas de representación y volumen de datos de las 12 tablas del schema `raw` en el Data Warehouse (`sgfood_dw`).

---

## 1. Control de Versiones y Procedimiento de Cambio

- **Versión:** 1
- **Fecha de aprobación:** 2026-10-09
- **Estado:** Vigente
- **Fuente de verdad ejecutable:** `Proyecto1/python/config/fuentes.yml`
- **Roles involucrados:** Rol A (Ingesta y orquestación) y Rol B (Modelado y dbt)

### Procedimiento de Cambio de Contrato
Toda modificación sobre las tablas o columnas de `raw` es un cambio de **zona amarilla** y requiere:
1. Propuesta explícita y consenso entre ambos integrantes.
2. Actualización atómica en el mismo commit de:
   - `Proyecto1/python/config/fuentes.yml` (fuente de verdad máquina).
   - `Proyecto1/sql/ddl/02_raw_tables.sql` (DDL de creación).
   - `Proyecto1/docs/contrato_raw.md` (documento de especificación).
3. Incremento del número de versión en los tres componentes.
4. Ejecución exitosa de la suite automatizada de pruebas de contrato (`pytest tests/contrato`).

---

## 2. Resumen de Tablas Raw

El schema `raw` aloja exactamente 12 tablas correspondientes a 7 entidades de la base transaccional (`oltp_sgfood`) y 5 archivos CSV externos.
Todas las columnas de negocio se almacenan como `TEXT` en la capa `raw`.

| Tabla `raw` | Tipo de fuente | Origen oficial | Granularidad | Filas esperadas |
|-------------|----------------|----------------|--------------|----------------:|
| `sucursal` | postgres | `oltp_sgfood.sucursal` | Una fila por sucursal | 6 |
| `categoria` | postgres | `oltp_sgfood.categoria` | Una fila por categoría | 8 |
| `marca` | postgres | `oltp_sgfood.marca` | Una fila por marca | 10 |
| `producto` | postgres | `oltp_sgfood.producto` | Una fila por producto | 80 |
| `cliente` | postgres | `oltp_sgfood.cliente` | Una fila por cliente | 250 |
| `venta` | postgres | `oltp_sgfood.venta` | Una fila por transacción de venta | 1200 |
| `venta_detalle` | postgres | `oltp_sgfood.venta_detalle` | Una fila por línea de detalle de venta | 3209 |
| `inventario_bodega` | csv | `inventario_bodega.csv` | Una fila por fecha de corte, sucursal y producto | 3840 |
| `proveedores_precios` | csv | `proveedores_precios.csv` | Una fila por proveedor, producto y fecha de vigencia | 103 |
| `devoluciones` | csv | `devoluciones.csv` | Una fila por devolución registrada | 80 |
| `metas_ventas` | csv | `metas_ventas.csv` | Una fila por periodo mensual y sucursal | 48 |
| `promociones` | csv | `promociones.csv` | Una fila por campaña promocional | 30 |

**Total de registros esperados en la ingesta completa:** 8.864 filas.

> [!NOTE]
> `casos_calidad_opcionales.csv` contiene casos de prueba sintéticos con anomalías intencionales. Conforme a la decisión D8 de steering, **no forma parte de la ingesta principal** y no tiene tabla en `raw`.

---

## 3. Reglas de Representación de Valores

Todas las transformaciones hacia tipos tipados (`INTEGER`, `NUMERIC`, `DATE`, `BOOLEAN`) se realizan en la capa `staging` de dbt (Rol B). Para asegurar consistencia y determinismo, la ingesta técnica garantiza las siguientes reglas de formato en `raw`:

| Caso | Formato y comportamiento en `raw` |
|------|-----------------------------------|
| **Valores nulos en BD fuente** | `NULL` nativo de SQL. |
| **Campos vacíos en CSV** | `NULL` nativo de SQL (cadenas vacías `""` se cargan como `NULL`). |
| **Valores de texto** | Cadena idéntica a la fuente, respetando mayúsculas, minúsculas, espacios y caracteres especiales. |
| **Números enteros** | Dígitos en base 10 sin separadores de miles (ej. `1200`). |
| **Números decimales (BD fuente)** | Cadena numérica con punto decimal según la escala definida en PostgreSQL (ej. `35.47`, `0.1500`). |
| **Números decimales (CSV)** | Cadena tal cual aparece en el CSV fuente (ej. `144615.3`). |
| **Fechas** | Formato estándar ISO 8601: `YYYY-MM-DD`. |
| **Booleanos** | Cadenas en minúsculas: `'true'` o `'false'`. |
| **Periodo en metas de ventas** | Formato de año y mes: `YYYY-MM` (sin componente de día). |
| **Codificación de CSV** | Leídos con `utf-8-sig` (removiendo el Byte Order Mark `\ufeff`). |

---

## 4. Columnas de Auditoría

Cada tabla del schema `raw` incluye al final de su definición dos columnas técnicas de trazabilidad y auditoría:

| Columna | Tipo de dato SQL | Restricción | Descripción |
|---------|------------------|-------------|-------------|
| `_loaded_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Fecha y hora UTC del momento exacto de la carga en el DW. Es homogénea para todas las filas de un lote de ingesta. |
| `_source` | `TEXT` | `NOT NULL` | Identificador de origen: `oltp_sgfood.<tabla>` para fuentes transaccionales, o nombre del archivo CSV (ej. `inventario_bodega.csv`). |

---

## 5. Especificación Detallada por Tabla

Las columnas de negocio se presentan en el orden ordinal estricto en que se almacenan en `raw`. La información de "Tipo esperado", "Clave o regla" y "Descripción" proviene del catálogo e insumos oficiales de SG-Food (`catalogo_insumos_sgfood.xlsx`).

### Tabla `sucursal`
- **Origen:** `oltp_sgfood.sucursal` (PostgreSQL OLTP)
- **Granularidad:** Una fila por sucursal
- **Filas esperadas:** 6 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_sucursal` | `TEXT` | `INTEGER` | PK | Identificador de sucursal |
| `nombre` | `TEXT` | `VARCHAR` | NOT NULL | Nombre comercial |
| `ciudad` | `TEXT` | `VARCHAR` | NOT NULL | Ciudad |
| `departamento` | `TEXT` | `VARCHAR` | NOT NULL | Departamento |

### Tabla `categoria`
- **Origen:** `oltp_sgfood.categoria` (PostgreSQL OLTP)
- **Granularidad:** Una fila por categoría
- **Filas esperadas:** 8 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_categoria` | `TEXT` | `INTEGER` | PK | Identificador de categoría |
| `nombre` | `TEXT` | `VARCHAR` | UQ | Nombre de categoría |

### Tabla `marca`
- **Origen:** `oltp_sgfood.marca` (PostgreSQL OLTP)
- **Granularidad:** Una fila por marca
- **Filas esperadas:** 10 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_marca` | `TEXT` | `INTEGER` | PK | Identificador de marca |
| `nombre` | `TEXT` | `VARCHAR` | UQ | Nombre de marca |

### Tabla `producto`
- **Origen:** `oltp_sgfood.producto` (PostgreSQL OLTP)
- **Granularidad:** Una fila por producto
- **Filas esperadas:** 80 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_producto` | `TEXT` | `INTEGER` | PK | Identificador de producto |
| `sku` | `TEXT` | `VARCHAR` | UQ | Código SKU |
| `nombre` | `TEXT` | `VARCHAR` | NOT NULL | Nombre |
| `id_categoria` | `TEXT` | `INTEGER` | FK categoria | Categoría |
| `id_marca` | `TEXT` | `INTEGER` | FK marca | Marca |
| `unidad_medida` | `TEXT` | `VARCHAR` | NOT NULL | Unidad |
| `costo_base` | `TEXT` | `NUMERIC(12,2)` | >= 0 | Costo de referencia |
| `precio_lista` | `TEXT` | `NUMERIC(12,2)` | >= 0 | Precio de lista |
| `activo` | `TEXT` | `BOOLEAN` | true/false | Estado |

### Tabla `cliente`
- **Origen:** `oltp_sgfood.cliente` (PostgreSQL OLTP)
- **Granularidad:** Una fila por cliente
- **Filas esperadas:** 250 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_cliente` | `TEXT` | `INTEGER` | PK | Identificador |
| `nit` | `TEXT` | `VARCHAR` | NOT NULL | NIT ficticio |
| `nombre` | `TEXT` | `VARCHAR` | NOT NULL | Nombre ficticio |
| `tipo_cliente` | `TEXT` | `VARCHAR` | NOT NULL | Segmento |
| `municipio` | `TEXT` | `VARCHAR` | Admite nulos | Municipio |
| `departamento` | `TEXT` | `VARCHAR` | Admite nulos | Departamento |
| `fecha_alta` | `TEXT` | `DATE` | NOT NULL | Alta |

### Tabla `venta`
- **Origen:** `oltp_sgfood.venta` (PostgreSQL OLTP)
- **Granularidad:** Una fila por venta
- **Filas esperadas:** 1200 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_venta` | `TEXT` | `BIGINT` | PK | Venta |
| `fecha` | `TEXT` | `DATE` | NOT NULL | Fecha |
| `id_cliente` | `TEXT` | `INTEGER` | FK cliente | Cliente |
| `id_sucursal` | `TEXT` | `INTEGER` | FK sucursal | Sucursal |
| `canal` | `TEXT` | `VARCHAR` | NOT NULL | Canal |
| `metodo_pago` | `TEXT` | `VARCHAR` | NOT NULL | Método |
| `estado` | `TEXT` | `VARCHAR` | NOT NULL | Estado |

### Tabla `venta_detalle`
- **Origen:** `oltp_sgfood.venta_detalle` (PostgreSQL OLTP)
- **Granularidad:** Una fila por línea de venta
- **Filas esperadas:** 3209 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_detalle` | `TEXT` | `BIGINT` | PK | Línea |
| `id_venta` | `TEXT` | `BIGINT` | FK venta | Venta |
| `id_producto` | `TEXT` | `INTEGER` | FK producto | Producto |
| `cantidad` | `TEXT` | `INTEGER` | > 0 | Unidades |
| `precio_unitario` | `TEXT` | `NUMERIC(12,2)` | >= 0 | Precio |
| `descuento` | `TEXT` | `NUMERIC(5,4)` | 0 a 1 | 0 a 1 |
| `subtotal` | `TEXT` | `NUMERIC(14,2)` | >= 0 | Importe neto |

### Tabla `inventario_bodega`
- **Origen:** `inventario_bodega.csv` (Archivo CSV)
- **Granularidad:** Una fila por snapshot de corte, sucursal y producto
- **Filas esperadas:** 3840 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `fecha_corte` | `TEXT` | `DATE` | NOT NULL | Snapshot |
| `id_sucursal` | `TEXT` | `INTEGER` | FK lógica | Sucursal |
| `id_producto` | `TEXT` | `INTEGER` | FK lógica | Producto |
| `stock_disponible` | `TEXT` | `INTEGER` | >= 0 | Existencia |
| `stock_minimo` | `TEXT` | `INTEGER` | >= 0 | Mínimo |
| `stock_maximo` | `TEXT` | `INTEGER` | >= 0 | Máximo |
| `lote` | `TEXT` | `VARCHAR` | NOT NULL | Lote |
| `fecha_vencimiento` | `TEXT` | `DATE` | NOT NULL | Vencimiento |

### Tabla `proveedores_precios`
- **Origen:** `proveedores_precios.csv` (Archivo CSV)
- **Granularidad:** Una fila por proveedor, producto y fecha de vigencia
- **Filas esperadas:** 103 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_proveedor` | `TEXT` | `INTEGER` | NOT NULL | Proveedor |
| `proveedor` | `TEXT` | `VARCHAR` | NOT NULL | Nombre |
| `id_producto` | `TEXT` | `INTEGER` | FK lógica | Producto |
| `costo_proveedor` | `TEXT` | `NUMERIC(12,2)` | >= 0 | Costo |
| `plazo_dias` | `TEXT` | `INTEGER` | >= 0 | Lead time |
| `fecha_vigencia` | `TEXT` | `DATE` | NOT NULL | Vigencia |

### Tabla `devoluciones`
- **Origen:** `devoluciones.csv` (Archivo CSV)
- **Granularidad:** Una fila por devolución
- **Filas esperadas:** 80 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_devolucion` | `TEXT` | `INTEGER` | PK lógica | Devolución |
| `fecha` | `TEXT` | `DATE` | NOT NULL | Fecha |
| `id_venta` | `TEXT` | `BIGINT` | FK lógica | Venta |
| `id_producto` | `TEXT` | `INTEGER` | FK lógica | Producto |
| `cantidad` | `TEXT` | `INTEGER` | > 0 | Cantidad |
| `motivo` | `TEXT` | `VARCHAR` | NOT NULL | Motivo |

### Tabla `metas_ventas`
- **Origen:** `metas_ventas.csv` (Archivo CSV)
- **Granularidad:** Una fila por periodo y sucursal
- **Filas esperadas:** 48 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `periodo` | `TEXT` | `VARCHAR(7)` | YYYY-MM | YYYY-MM |
| `id_sucursal` | `TEXT` | `INTEGER` | FK lógica | Sucursal |
| `meta_ventas` | `TEXT` | `NUMERIC(14,2)` | >= 0 | Meta monetaria |
| `meta_unidades` | `TEXT` | `INTEGER` | >= 0 | Meta de unidades |

### Tabla `promociones`
- **Origen:** `promociones.csv` (Archivo CSV)
- **Granularidad:** Una fila por campaña promocional
- **Filas esperadas:** 30 filas

| Columna | Tipo en `raw` | Tipo esperado | Clave / Regla | Descripción del diccionario |
|---------|---------------|---------------|---------------|-----------------------------|
| `id_promocion` | `TEXT` | `INTEGER` | PK lógica | Promoción |
| `nombre` | `TEXT` | `VARCHAR` | NOT NULL | Campaña |
| `fecha_inicio` | `TEXT` | `DATE` | NOT NULL | Inicio |
| `fecha_fin` | `TEXT` | `DATE` | NOT NULL | Fin |
| `id_categoria` | `TEXT` | `INTEGER` | FK lógica | Categoría |
| `porcentaje_descuento` | `TEXT` | `NUMERIC(5,4)` | 0 a 1 | 0 a 1 |

---

## 6. Límites y Garantías del Contrato

### Lo que este contrato GARANTIZA en `raw`:
1. Existencia exacta de las 12 tablas con los nombres especificados.
2. Presencia de todas las columnas de negocio en el orden exacto especificado, todas como tipo `TEXT`.
3. Inclusión obligatoria de las columnas de auditoría `_loaded_at` y `_source` al final de cada tabla.
4. Preservación del contenido de la fuente original (sin alteraciones de mayúsculas ni recortes arbitrarios).
5. Ingesta idempotente: recargas completas truncan y refrescan sin duplicación.

### Lo que este contrato NO GARANTIZA en `raw`:
1. **Integridad referencial:** Las tablas `raw` no imponen `FOREIGN KEY`. Las relaciones deben ser validadas en dbt (`relationships` tests).
2. **Unicidad obligatoria:** Las tablas `raw` no imponen `PRIMARY KEY` o restricciones `UNIQUE`. La unicidad de claves se audita en dbt (`unique` tests).
3. **Validación de rangos numéricos o de fechas:** Valores fuera de rango o con formato anómalo se conservan en texto en `raw` para permitir auditoría y detección de calidad de datos en `staging` mediante pruebas dbt.
