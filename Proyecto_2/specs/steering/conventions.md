# Convenciones — Proyecto 2

Reglas de trabajo para ambos integrantes. Arquitectura, zonas y contrato: [architecture.md](architecture.md).

## Git

| Regla | Detalle |
|-------|---------|
| Mensajes | Conventional Commits `<tipo>: <descripción>`, **sin alcance**. La descripción va **en español**, en presente, con **50 caracteres como máximo** y sin punto final. Tipos estándar: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `style`, `build`, `ci`, `chore`. Ejemplo: `feat: publica vista de contrato con validaciones`. |
| Autoría | Cada integrante hace commit de su propio trabajo, en commits pequeños y granulares. El historial es la evidencia del trabajo en pareja. |
| Trailers | Sin trailers de atribución a IA. |
| Ramas | `feat/p2-a-*` para A, `feat/p2-b-*` para B. Nunca se hace push a la rama del otro. |
| Integración | Pull request a `main` revisado por el otro integrante. Sin `force push`. |

## Estructura SQL

| Ruta | Contenido |
|------|-----------|
| `Proyecto_2/sql/contract/` | Datasets y vista del contrato (zona amarilla) |
| `Proyecto_2/sql/a_<nn>_<tema>.sql` | Scripts de A |
| `Proyecto_2/sql/b_<nn>_<tema>.sql` | Scripts de B |

- Cada script empieza con un comentario de encabezado: propósito, dueño, entradas y salidas.
- Cada bloque lleva un comentario que explica su finalidad; el enunciado exige scripts comentados.
- Los nombres de tabla van completamente calificados y entre backticks: `` `ss2-g16-proyecto2.p2_contract.v_trips_clean` ``.

## Ejecutar SQL en Windows

Git Bash rompe `bq` y los backticks. El archivo se pasa por `cmd`:

```bash
cmd //c "set PYTHONUTF8=1&& bq --project_id=ss2-g16-proyecto2 query --use_legacy_sql=false < Proyecto_2\sql\<ruta>\<archivo>.sql"
```

- `PYTHONUTF8=1` es obligatorio: sin esa variable, `bq` lee el archivo como cp1252 y los textos con tildes quedan corruptos (por ejemplo, «común» se guarda como «comÃºn»).
- La ruta del redireccionamiento usa `\` porque la interpreta `cmd`.
- **Nunca pasar SQL inline dentro de `cmd //c "..."`**: `cmd` interpreta `>`, `<` y `|` del SQL como redirecciones y crea archivos vacíos en la raíz del repo (pasó con `1` y con `TIMESTAMP_SUB(CURRENT_TIMESTAMP()`). El SQL siempre va en un archivo bajo `$TEMP` y entra por `<`.
- Se usa la configuración de gcloud `ss2-p2`.

## Control de costos

- Toda consulta nueva se ejecuta primero con `--dry_run` y se registran los bytes procesados.
- El crédito de prueba tiene USD 282 disponibles.
- En la fase 1 del contrato, la vista lee la tabla pública sin particiones: cada consulta escanea las columnas usadas de los 36.26 millones de filas. Conviene que B materialice sus `features_*` en lugar de consultar la vista repetidamente.

## Evidencia

- Ruta: `Proyecto_2/evidencia/<nn>_<tema>.<png|txt|json>`.
- La salida de texto se guarda como `.txt`; `*.log` está en `.gitignore`.
- No se inventan cifras: todo número del README sale de una salida de consulta guardada.

## Antes de abrir un pull request

- [ ] Los commits siguen `<tipo>: <descripción>` con tipos estándar, sin alcance, con la descripción en español de 50 caracteres como máximo y sin trailers de IA.
- [ ] Solo se tocan rutas de la zona verde propia, o hay acuerdo explícito para la zona amarilla.
- [ ] Cada script nuevo tiene encabezado y comentarios por bloque.
- [ ] Cada consulta nueva pasó por `--dry_run` y sus bytes quedaron registrados.
- [ ] La evidencia de cada resultado está guardada en `Proyecto_2/evidencia/`.
- [ ] Las cifras del README coinciden con la evidencia guardada.
- [ ] Si se tocó el contrato, el esquema de `v_trips_clean` no cambió o el cambio está acordado.
