"""Interfaz de línea de comandos para sgfood_ingesta."""
import argparse
import logging
import sys
from typing import Optional, Sequence

from sgfood_ingesta.config import listar_fuentes
from sgfood_ingesta.errores import ConfiguracionInvalida, ErrorIngesta, FuenteDesconocida
from sgfood_ingesta.ingesta import cargar_fuente, cargar_todas


logger = logging.getLogger(__name__)


def configurar_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sgfood_ingesta",
        description="Ingesta técnica de datos crudos hacia el schema raw del Data Warehouse SG-Food.",
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--tabla",
        metavar="TABLA",
        help="Carga únicamente la tabla especificada (ej. sucursal, devoluciones).",
    )
    grupo.add_argument(
        "--listar",
        action="store_true",
        help="Muestra las fuentes configuradas y finaliza.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    configurar_logging()
    parser = crear_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return code

    try:
        if args.listar:
            fuentes = listar_fuentes()
            print(f"Fuentes configuradas ({len(fuentes)}):")
            for f in fuentes:
                print(f"  - {f.tabla_raw} [{f.tipo}]: origen={f.origen}, columnas={len(f.columnas)}")
            return 0

        if args.tabla:
            cargar_fuente(args.tabla)
            return 0

        # Sin argumentos: carga todas las tablas
        cargar_todas()
        return 0

    except (ConfiguracionInvalida, FuenteDesconocida) as exc:
        sys.stderr.write(f"Error de configuracion/argumentos: {exc}\n")
        return 2
    except ErrorIngesta as exc:
        logger.error("Error durante la ingesta: %s", exc)
        return 1
    except Exception:
        # La traza completa es lo que permite diagnosticar errores de base de datos o de red.
        logger.exception("Fallo inesperado durante la ingesta")
        return 1


if __name__ == "__main__":
    sys.exit(main())
