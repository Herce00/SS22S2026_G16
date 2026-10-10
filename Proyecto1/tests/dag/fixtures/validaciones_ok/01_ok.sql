-- Validación que no debe devolver filas si los datos son consistentes
SELECT * FROM raw.sucursal WHERE id_sucursal IS NULL;
