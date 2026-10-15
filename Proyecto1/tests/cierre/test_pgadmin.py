"""R8: pgAdmin opcional, con version fija y sin credenciales literales (analisis estatico del compose)."""
import os
import re
import subprocess

import pytest
import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _compose():
    with open(os.path.join(RAIZ, "docker-compose.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _pgadmin():
    servicios = [c for c in _compose()["services"].values() if "pgadmin4" in c.get("image", "")]
    assert len(servicios) == 1, "debe haber exactamente un servicio pgAdmin"
    return servicios[0]


def test_ninguna_imagen_sin_version_fija():
    imagenes = [c["image"] for c in _compose()["services"].values() if "image" in c]
    for imagen in imagenes:
        nombre, _, etiqueta = imagen.partition(":")
        assert etiqueta and etiqueta != "latest", f"{imagen} debe fijar una version"


def test_pgadmin_usa_version_fija():
    assert re.fullmatch(r"dpage/pgadmin4:\d+\.\d+(\.\d+)?", _pgadmin()["image"])


def test_pgadmin_pertenece_al_perfil_herramientas():
    assert _pgadmin().get("profiles") == ["herramientas"]


def test_pgadmin_toma_credenciales_y_puerto_de_variables():
    svc = _pgadmin()
    env = svc["environment"]
    # el correo puede tener un valor por defecto no personal; la contrasena nunca
    assert re.fullmatch(r"\$\{PGADMIN_EMAIL(:-[^}@]+@example\.com)?\}", env["PGADMIN_DEFAULT_EMAIL"])
    assert re.fullmatch(r"\$\{PGADMIN_PASSWORD(:-)?\}", env["PGADMIN_DEFAULT_PASSWORD"])
    assert svc["ports"] == ["${PGADMIN_PORT:-8081}:80"]


def test_pgadmin_monta_un_unico_volumen_de_datos():
    assert _pgadmin()["volumes"] == ["pgadmin_data:/var/lib/pgadmin"]
    assert "pgadmin_data" in _compose()["volumes"]


def test_env_example_define_variables_de_pgadmin_sin_datos_personales():
    ruta = os.path.join(RAIZ, ".env.example")
    with open(ruta, encoding="utf-8") as f:
        valores = dict(
            l.strip().split("=", 1) for l in f if l.strip() and not l.startswith("#") and "=" in l
        )
    for var in ("PGADMIN_EMAIL", "PGADMIN_PASSWORD", "PGADMIN_PORT"):
        assert var in valores, f"falta {var} en .env.example"
    assert valores["PGADMIN_EMAIL"].endswith("@example.com")
    assert valores["PGADMIN_PASSWORD"].startswith("cambiar_")


def _servicios(*args):
    res = subprocess.run(
        ["docker", "compose", *args, "config", "--services"],
        capture_output=True, text=True, cwd=RAIZ,
    )
    assert res.returncode == 0, res.stderr
    return set(res.stdout.split())


@pytest.mark.integracion
def test_up_sin_perfil_no_incluye_pgadmin_y_con_perfil_si():
    sin_perfil = _servicios()
    con_perfil = _servicios("--profile", "herramientas")
    assert not [s for s in sin_perfil if "pgadmin" in s.lower()]
    assert [s for s in con_perfil if "pgadmin" in s.lower()]
