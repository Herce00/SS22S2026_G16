"""
Pruebas estáticas de configuración del entorno.
Nota: test_docker_compose_config queda en rojo de forma intencional hasta T4
cuando se crea docker-compose.yml.
"""
from conftest import run_docker_compose

def test_docker_compose_config(proyecto1_dir):
    """Verifica que 'docker compose config' se ejecute con éxito."""
    res = run_docker_compose("config", cwd=proyecto1_dir)
    assert res.returncode == 0, f"docker compose config falló con retorno {res.returncode}:\n{res.stderr}"
