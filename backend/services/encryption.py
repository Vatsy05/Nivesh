"""
AES-256-CBC encryption/decryption for transaction data at rest.
"""
import os
import base64
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

from app.config import settings


def _get_key() -> bytes:
    """Derive a 32-byte AES-256 key from the ENCRYPTION_KEY setting."""
    raw_key = settings.ENCRYPTION_KEY
    try:
        decoded = base64.b64decode(raw_key)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


def encrypt_data(data: bytes) -> bytes:
    """Encrypt data using AES-256-CBC. Returns [16-byte IV][ciphertext]."""
    key = _get_key()
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return iv + ciphertext


def decrypt_data(encrypted: bytes) -> bytes:
    """Decrypt AES-256-CBC encrypted data. Expects [16-byte IV][ciphertext]."""
    key = _get_key()
    iv = encrypted[:16]
    ciphertext = encrypted[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def encrypt_string(text: str) -> str:
    """Encrypt a string and return base64-encoded ciphertext."""
    encrypted = encrypt_data(text.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_string(encoded: str) -> str:
    """Decrypt a base64-encoded ciphertext string."""
    encrypted = base64.b64decode(encoded)
    return decrypt_data(encrypted).decode("utf-8")
