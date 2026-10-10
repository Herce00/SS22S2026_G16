-- =============================================================================
-- Tablas del Schema Raw (sgfood_dw)
-- Capa de datos crudos fiel a la fuente (12 tablas: 7 postgres, 5 csv)
-- Todas las columnas de negocio son de tipo TEXT.
-- Columnas de auditoría: _loaded_at (TIMESTAMPTZ) y _source (TEXT).
-- Sin claves primarias, claves foráneas ni restricciones sobre columnas de negocio.
-- =============================================================================

-- 1. sucursal (Fuente: oltp_sgfood.sucursal)
CREATE TABLE IF NOT EXISTS raw.sucursal (
    id_sucursal TEXT,
    nombre TEXT,
    ciudad TEXT,
    departamento TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.sucursal IS 'Fuente: oltp_sgfood.sucursal';

-- 2. categoria (Fuente: oltp_sgfood.categoria)
CREATE TABLE IF NOT EXISTS raw.categoria (
    id_categoria TEXT,
    nombre TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.categoria IS 'Fuente: oltp_sgfood.categoria';

-- 3. marca (Fuente: oltp_sgfood.marca)
CREATE TABLE IF NOT EXISTS raw.marca (
    id_marca TEXT,
    nombre TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.marca IS 'Fuente: oltp_sgfood.marca';

-- 4. producto (Fuente: oltp_sgfood.producto)
CREATE TABLE IF NOT EXISTS raw.producto (
    id_producto TEXT,
    sku TEXT,
    nombre TEXT,
    id_categoria TEXT,
    id_marca TEXT,
    unidad_medida TEXT,
    costo_base TEXT,
    precio_lista TEXT,
    activo TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.producto IS 'Fuente: oltp_sgfood.producto';

-- 5. cliente (Fuente: oltp_sgfood.cliente)
CREATE TABLE IF NOT EXISTS raw.cliente (
    id_cliente TEXT,
    nit TEXT,
    nombre TEXT,
    tipo_cliente TEXT,
    municipio TEXT,
    departamento TEXT,
    fecha_alta TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.cliente IS 'Fuente: oltp_sgfood.cliente';

-- 6. venta (Fuente: oltp_sgfood.venta)
CREATE TABLE IF NOT EXISTS raw.venta (
    id_venta TEXT,
    fecha TEXT,
    id_cliente TEXT,
    id_sucursal TEXT,
    canal TEXT,
    metodo_pago TEXT,
    estado TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.venta IS 'Fuente: oltp_sgfood.venta';

-- 7. venta_detalle (Fuente: oltp_sgfood.venta_detalle)
CREATE TABLE IF NOT EXISTS raw.venta_detalle (
    id_detalle TEXT,
    id_venta TEXT,
    id_producto TEXT,
    cantidad TEXT,
    precio_unitario TEXT,
    descuento TEXT,
    subtotal TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.venta_detalle IS 'Fuente: oltp_sgfood.venta_detalle';

-- 8. inventario_bodega (Fuente: inventario_bodega.csv)
CREATE TABLE IF NOT EXISTS raw.inventario_bodega (
    fecha_corte TEXT,
    id_sucursal TEXT,
    id_producto TEXT,
    stock_disponible TEXT,
    stock_minimo TEXT,
    stock_maximo TEXT,
    lote TEXT,
    fecha_vencimiento TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.inventario_bodega IS 'Fuente: inventario_bodega.csv';

-- 9. proveedores_precios (Fuente: proveedores_precios.csv)
CREATE TABLE IF NOT EXISTS raw.proveedores_precios (
    id_proveedor TEXT,
    proveedor TEXT,
    id_producto TEXT,
    costo_proveedor TEXT,
    plazo_dias TEXT,
    fecha_vigencia TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.proveedores_precios IS 'Fuente: proveedores_precios.csv';

-- 10. devoluciones (Fuente: devoluciones.csv)
CREATE TABLE IF NOT EXISTS raw.devoluciones (
    id_devolucion TEXT,
    fecha TEXT,
    id_venta TEXT,
    id_producto TEXT,
    cantidad TEXT,
    motivo TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.devoluciones IS 'Fuente: devoluciones.csv';

-- 11. metas_ventas (Fuente: metas_ventas.csv)
CREATE TABLE IF NOT EXISTS raw.metas_ventas (
    periodo TEXT,
    id_sucursal TEXT,
    meta_ventas TEXT,
    meta_unidades TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.metas_ventas IS 'Fuente: metas_ventas.csv';

-- 12. promociones (Fuente: promociones.csv)
CREATE TABLE IF NOT EXISTS raw.promociones (
    id_promocion TEXT,
    nombre TEXT,
    fecha_inicio TEXT,
    fecha_fin TEXT,
    id_categoria TEXT,
    porcentaje_descuento TEXT,
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _source TEXT NOT NULL
);
COMMENT ON TABLE raw.promociones IS 'Fuente: promociones.csv';
