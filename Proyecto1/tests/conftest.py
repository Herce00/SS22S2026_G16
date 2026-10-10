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

def get_env_variable(proyecto1_dir, var_name, default=None):
    """Lee una variable de entorno desde .env si existe."""
    env_path = os.path.join(proyecto1_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{var_name}="):
                    return line.split("=", 1)[1].strip()
    return default

@pytest.fixture(scope="session")
def env_config(proyecto1_dir):
    """Carga las variables de entorno de .env en un diccionario."""
    config = {}
    env_path = os.path.join(proyecto1_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
    return config
