-- DDL de referencia del schema marts: referencia generada, solo documentacion.
-- Fecha de generacion: 2026-10-14
-- Comando: pg_dump --schema-only --schema=marts --no-owner --no-privileges
-- Origen: la base sgfood_dw despues de una ejecucion del DAG sgfood_elt.
-- dbt crea y recrea estas tablas y restricciones en cada ejecucion (dbt run).
-- Este archivo no se ejecuta en la inicializacion del DW: vive en una subcarpeta que
-- /docker-entrypoint-initdb.d no recorre, porque crearia tablas que dbt espera crear.
-- ---- fin del encabezado ----
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.15 (Debian 16.15-1.pgdg13+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: marts; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA marts;


--
-- Name: SCHEMA marts; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA marts IS 'Capa analítica dimensional (hechos y dimensiones) modelada con dbt';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: dim_categoria; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.dim_categoria (
    categoria_key text NOT NULL,
    id_categoria integer,
    nombre text
);


--
-- Name: dim_cliente; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.dim_cliente (
    cliente_key text NOT NULL,
    id_cliente integer,
    nit text,
    nombre text,
    tipo_cliente text,
    municipio text,
    departamento text,
    fecha_alta date
);


--
-- Name: dim_fecha; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.dim_fecha (
    fecha_key integer NOT NULL,
    fecha date,
    dia integer,
    mes integer,
    nombre_mes text,
    trimestre integer,
    anio integer,
    semana_anio integer,
    es_fin_de_semana boolean
);


--
-- Name: dim_marca; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.dim_marca (
    marca_key text NOT NULL,
    id_marca integer,
    nombre text
);


--
-- Name: dim_producto; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.dim_producto (
    producto_key text NOT NULL,
    id_producto integer,
    sku text,
    nombre text,
    categoria_key text,
    marca_key text,
    unidad_medida text,
    costo_base numeric,
    precio_lista numeric,
    activo boolean
);


--
-- Name: dim_promocion; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.dim_promocion (
    promocion_key text NOT NULL,
    id_promocion integer,
    nombre text,
    fecha_inicio_key integer,
    fecha_fin_key integer,
    categoria_key text,
    porcentaje_descuento numeric
);


--
-- Name: dim_sucursal; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.dim_sucursal (
    sucursal_key text NOT NULL,
    id_sucursal integer,
    nombre text,
    ciudad text,
    departamento text
);


--
-- Name: fct_devoluciones; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.fct_devoluciones (
    devolucion_key integer NOT NULL,
    id_devolucion integer,
    fecha_key integer,
    id_venta bigint,
    producto_key text,
    cantidad integer,
    motivo text
);


--
-- Name: fct_inventario_snapshot; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.fct_inventario_snapshot (
    inventario_snapshot_key text NOT NULL,
    fecha_key integer,
    sucursal_key text,
    producto_key text,
    lote text,
    fecha_vencimiento date,
    stock_disponible integer,
    stock_minimo integer,
    stock_maximo integer,
    stock_faltante integer,
    stock_sobrante integer,
    esta_bajo_minimo boolean,
    esta_sobre_maximo boolean
);


--
-- Name: fct_metas_ventas; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.fct_metas_ventas (
    meta_key text NOT NULL,
    periodo_key integer,
    periodo text,
    sucursal_key text,
    meta_ventas numeric,
    meta_unidades integer
);


--
-- Name: fct_precios_proveedor; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.fct_precios_proveedor (
    precio_proveedor_key text NOT NULL,
    id_proveedor integer,
    proveedor text,
    producto_key text,
    fecha_key integer,
    costo_proveedor numeric,
    plazo_dias integer
);


--
-- Name: fct_ventas_linea; Type: TABLE; Schema: marts; Owner: -
--

CREATE TABLE marts.fct_ventas_linea (
    venta_linea_key text NOT NULL,
    id_detalle bigint,
    id_venta bigint,
    fecha_key integer,
    cliente_key text,
    sucursal_key text,
    producto_key text,
    canal text,
    metodo_pago text,
    estado text,
    cantidad integer,
    precio_unitario numeric,
    descuento numeric,
    subtotal numeric,
    importe_bruto numeric,
    importe_descuento numeric,
    _loaded_at timestamp with time zone
);


--
-- Name: dim_categoria pk_dim_categoria; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_categoria
    ADD CONSTRAINT pk_dim_categoria PRIMARY KEY (categoria_key);


--
-- Name: dim_cliente pk_dim_cliente; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_cliente
    ADD CONSTRAINT pk_dim_cliente PRIMARY KEY (cliente_key);


--
-- Name: dim_fecha pk_dim_fecha; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_fecha
    ADD CONSTRAINT pk_dim_fecha PRIMARY KEY (fecha_key);


--
-- Name: dim_marca pk_dim_marca; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_marca
    ADD CONSTRAINT pk_dim_marca PRIMARY KEY (marca_key);


--
-- Name: dim_producto pk_dim_producto; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_producto
    ADD CONSTRAINT pk_dim_producto PRIMARY KEY (producto_key);


--
-- Name: dim_promocion pk_dim_promocion; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_promocion
    ADD CONSTRAINT pk_dim_promocion PRIMARY KEY (promocion_key);


--
-- Name: dim_sucursal pk_dim_sucursal; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_sucursal
    ADD CONSTRAINT pk_dim_sucursal PRIMARY KEY (sucursal_key);


--
-- Name: fct_devoluciones pk_fct_devoluciones; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_devoluciones
    ADD CONSTRAINT pk_fct_devoluciones PRIMARY KEY (devolucion_key);


--
-- Name: fct_inventario_snapshot pk_fct_inventario_snapshot; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_inventario_snapshot
    ADD CONSTRAINT pk_fct_inventario_snapshot PRIMARY KEY (inventario_snapshot_key);


--
-- Name: fct_metas_ventas pk_fct_metas_ventas; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_metas_ventas
    ADD CONSTRAINT pk_fct_metas_ventas PRIMARY KEY (meta_key);


--
-- Name: fct_precios_proveedor pk_fct_precios_proveedor; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_precios_proveedor
    ADD CONSTRAINT pk_fct_precios_proveedor PRIMARY KEY (precio_proveedor_key);


--
-- Name: fct_ventas_linea pk_fct_ventas_linea; Type: CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_ventas_linea
    ADD CONSTRAINT pk_fct_ventas_linea PRIMARY KEY (venta_linea_key);


--
-- Name: dim_producto fk_dim_producto_categoria_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_producto
    ADD CONSTRAINT fk_dim_producto_categoria_key FOREIGN KEY (categoria_key) REFERENCES marts.dim_categoria(categoria_key);


--
-- Name: dim_producto fk_dim_producto_marca_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_producto
    ADD CONSTRAINT fk_dim_producto_marca_key FOREIGN KEY (marca_key) REFERENCES marts.dim_marca(marca_key);


--
-- Name: dim_promocion fk_dim_promocion_categoria_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_promocion
    ADD CONSTRAINT fk_dim_promocion_categoria_key FOREIGN KEY (categoria_key) REFERENCES marts.dim_categoria(categoria_key);


--
-- Name: dim_promocion fk_dim_promocion_fecha_fin_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_promocion
    ADD CONSTRAINT fk_dim_promocion_fecha_fin_key FOREIGN KEY (fecha_fin_key) REFERENCES marts.dim_fecha(fecha_key);


--
-- Name: dim_promocion fk_dim_promocion_fecha_inicio_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.dim_promocion
    ADD CONSTRAINT fk_dim_promocion_fecha_inicio_key FOREIGN KEY (fecha_inicio_key) REFERENCES marts.dim_fecha(fecha_key);


--
-- Name: fct_devoluciones fk_fct_devoluciones_fecha_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_devoluciones
    ADD CONSTRAINT fk_fct_devoluciones_fecha_key FOREIGN KEY (fecha_key) REFERENCES marts.dim_fecha(fecha_key);


--
-- Name: fct_devoluciones fk_fct_devoluciones_producto_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_devoluciones
    ADD CONSTRAINT fk_fct_devoluciones_producto_key FOREIGN KEY (producto_key) REFERENCES marts.dim_producto(producto_key);


--
-- Name: fct_inventario_snapshot fk_fct_inventario_snapshot_fecha_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_inventario_snapshot
    ADD CONSTRAINT fk_fct_inventario_snapshot_fecha_key FOREIGN KEY (fecha_key) REFERENCES marts.dim_fecha(fecha_key);


--
-- Name: fct_inventario_snapshot fk_fct_inventario_snapshot_producto_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_inventario_snapshot
    ADD CONSTRAINT fk_fct_inventario_snapshot_producto_key FOREIGN KEY (producto_key) REFERENCES marts.dim_producto(producto_key);


--
-- Name: fct_inventario_snapshot fk_fct_inventario_snapshot_sucursal_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_inventario_snapshot
    ADD CONSTRAINT fk_fct_inventario_snapshot_sucursal_key FOREIGN KEY (sucursal_key) REFERENCES marts.dim_sucursal(sucursal_key);


--
-- Name: fct_metas_ventas fk_fct_metas_ventas_periodo_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_metas_ventas
    ADD CONSTRAINT fk_fct_metas_ventas_periodo_key FOREIGN KEY (periodo_key) REFERENCES marts.dim_fecha(fecha_key);


--
-- Name: fct_metas_ventas fk_fct_metas_ventas_sucursal_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_metas_ventas
    ADD CONSTRAINT fk_fct_metas_ventas_sucursal_key FOREIGN KEY (sucursal_key) REFERENCES marts.dim_sucursal(sucursal_key);


--
-- Name: fct_precios_proveedor fk_fct_precios_proveedor_fecha_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_precios_proveedor
    ADD CONSTRAINT fk_fct_precios_proveedor_fecha_key FOREIGN KEY (fecha_key) REFERENCES marts.dim_fecha(fecha_key);


--
-- Name: fct_precios_proveedor fk_fct_precios_proveedor_producto_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_precios_proveedor
    ADD CONSTRAINT fk_fct_precios_proveedor_producto_key FOREIGN KEY (producto_key) REFERENCES marts.dim_producto(producto_key);


--
-- Name: fct_ventas_linea fk_fct_ventas_linea_cliente_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_ventas_linea
    ADD CONSTRAINT fk_fct_ventas_linea_cliente_key FOREIGN KEY (cliente_key) REFERENCES marts.dim_cliente(cliente_key);


--
-- Name: fct_ventas_linea fk_fct_ventas_linea_fecha_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_ventas_linea
    ADD CONSTRAINT fk_fct_ventas_linea_fecha_key FOREIGN KEY (fecha_key) REFERENCES marts.dim_fecha(fecha_key);


--
-- Name: fct_ventas_linea fk_fct_ventas_linea_producto_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_ventas_linea
    ADD CONSTRAINT fk_fct_ventas_linea_producto_key FOREIGN KEY (producto_key) REFERENCES marts.dim_producto(producto_key);


--
-- Name: fct_ventas_linea fk_fct_ventas_linea_sucursal_key; Type: FK CONSTRAINT; Schema: marts; Owner: -
--

ALTER TABLE ONLY marts.fct_ventas_linea
    ADD CONSTRAINT fk_fct_ventas_linea_sucursal_key FOREIGN KEY (sucursal_key) REFERENCES marts.dim_sucursal(sucursal_key);


--
-- PostgreSQL database dump complete
--


