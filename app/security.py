"""Funções pequenas e autocontidas para armazenamento seguro de senhas."""

import base64
import binascii
import hashlib
import hmac
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
PASSWORD_RESET_SALT = "password-reset"


def hash_password(password: str) -> str:
    """Gera um hash PBKDF2 com salt aleatório; a senha original nunca é armazenada."""

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "$".join(
        (
            ALGORITHM,
            str(ITERATIONS),
            base64.urlsafe_b64encode(salt).decode(),
            base64.urlsafe_b64encode(digest).decode(),
        )
    )


def verify_password(password: str, encoded: str | None) -> bool:
    """Compara uma senha com o hash sem revelar diferenças de tempo relevantes."""

    if not encoded:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
    except (TypeError, ValueError, binascii.Error):
        return False

    calculated = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(calculated, expected)


def create_password_reset_token(
    user_id: int, email: str, password_hash: str, secret: str
) -> str:
    """Cria um token assinado sem armazenar a senha ou o token no banco."""

    serializer = URLSafeTimedSerializer(secret_key=secret, salt=PASSWORD_RESET_SALT)
    password_version = hashlib.sha256(password_hash.encode()).hexdigest()[:16]
    return serializer.dumps(
        {"user_id": user_id, "email": email, "password_version": password_version}
    )


def read_password_reset_token(token: str, secret: str, max_age: int = 3600) -> dict | None:
    """Valida assinatura e expiração de um link de recuperação."""

    serializer = URLSafeTimedSerializer(secret_key=secret, salt=PASSWORD_RESET_SALT)
    try:
        payload = serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("user_id"), int) or not isinstance(payload.get("email"), str):
        return None
    return payload
