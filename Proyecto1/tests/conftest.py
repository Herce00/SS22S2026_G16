import os
import subprocess
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "integracion: prueba de integracion que requiere contenedores en ejecucion")
    config.addinivalue_line("markers", "lenta: prueba lenta (ej. ciclo completo de down/up)")

@pytest.fixture(scope="session")
def proyecto1_dir():
    """Retorna la ruta absoluta del directorio Proyecto1."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_docker_compose(*args, cwd=None):
    """Ejecuta un comando de docker compose y retorna el resultado."""
    cmd = ["docker", "compose"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
