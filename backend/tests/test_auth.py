from app.api.deps import Actor
from app.security import crear_token, hash_password, leer_token, verificar_password


def test_password_hash_y_verificacion():
    h = hash_password("secreta123")
    assert h.startswith("scrypt$") and "secreta123" not in h
    assert verificar_password("secreta123", h)
    assert not verificar_password("otra", h)
    assert not verificar_password("x", "basura")


def test_token_ida_y_vuelta():
    assert leer_token(crear_token(42)) == 42
    assert leer_token("no.es.un.token") is None


def test_permisos_por_negocio():
    admin = Actor(usuario=None, es_admin=True, negocio_id=None)
    negocio = Actor(usuario=None, es_admin=False, negocio_id=7)
    assert admin.puede_ver(1) and admin.puede_ver(7)
    assert negocio.puede_ver(7) and not negocio.puede_ver(8)
