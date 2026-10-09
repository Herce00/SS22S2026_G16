import json
import os
import urllib.request
import urllib.error
import pytest

def get_env_variable(proyecto1_dir, var_name, default=None):
    env_path = os.path.join(proyecto1_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{var_name}="):
                    return line.split("=", 1)[1].strip()
    return default

@pytest.mark.integracion
def test_admin_user_login(proyecto1_dir):
    """Verifica autenticación exitosa contra la API con credenciales de .env y fallo con contraseña incorrecta."""
    port = get_env_variable(proyecto1_dir, "AIRFLOW_PORT", "8080")
    user = get_env_variable(proyecto1_dir, "AIRFLOW_ADMIN_USER", "admin")
    password = get_env_variable(proyecto1_dir, "AIRFLOW_ADMIN_PASSWORD", "admin")

    token_url = f"http://localhost:{port}/auth/token"

    # 1. Probar login con credenciales correctas -> debe retornar 201 y un access_token
    payload_valid = json.dumps({"username": user, "password": password}).encode("utf-8")
    req_valid = urllib.request.Request(
        token_url,
        data=payload_valid,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req_valid, timeout=10) as resp:
            assert resp.status == 201, f"Se esperaba 201 pero se obtuvo {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            assert "access_token" in data, "La respuesta no contiene access_token"
            access_token = data["access_token"]
    except urllib.error.HTTPError as e:
        pytest.fail(f"Fallo al autenticar usuario administrador con credenciales válidas: HTTP {e.code} ({e.reason})")

    # 2. Probar acceso a la API protegida (/api/v2/dags) con el token obtenido -> debe retornar 200
    api_url = f"http://localhost:{port}/api/v2/dags"
    req_api = urllib.request.Request(
        api_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    with urllib.request.urlopen(req_api, timeout=10) as resp_api:
        assert resp_api.status == 200, f"Se esperaba 200 pero se obtuvo {resp_api.status}"

    # 3. Probar login con contraseña incorrecta -> debe retornar 401
    payload_invalid = json.dumps({"username": user, "password": "password_incorrecto_123"}).encode("utf-8")
    req_invalid = urllib.request.Request(
        token_url,
        data=payload_invalid,
        headers={"Content-Type": "application/json"}
    )

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req_invalid, timeout=10)
    assert exc_info.value.code == 401, f"Se esperaba 401 para credenciales inválidas pero se obtuvo {exc_info.value.code}"
