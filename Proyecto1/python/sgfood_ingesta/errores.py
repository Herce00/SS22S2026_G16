"""Jerarquía de excepciones del paquete sgfood_ingesta."""


class ErrorIngesta(Exception):
    """Excepción base para todos los errores del proceso de ingesta."""
    pass


class ConfiguracionInvalida(ErrorIngesta):
    """El archivo fuentes.yml o las variables de entorno son inválidas o incompletas."""
    pass


class FuenteDesconocida(ErrorIngesta):
    """La tabla solicitada no está declarada en la configuración."""
    pass


class EncabezadoInvalido(ErrorIngesta):
    """El encabezado del archivo CSV no coincide con las columnas declaradas."""
    pass


class FilaInvalida(ErrorIngesta):
    """Una fila del archivo CSV tiene una cantidad incorrecta de campos."""

    def __init__(self, mensaje: str, linea: int | None = None):
        super().__init__(mensaje)
        self.linea = linea


class ConteoInconsistente(ErrorIngesta):
    """La cantidad de filas cargadas en raw no coincide con las filas leídas de la fuente."""
    pass


class ValidacionFallida(ErrorIngesta):
    """Una validación de calidad de datos, conteos o integridad referencial falló."""
    pass

