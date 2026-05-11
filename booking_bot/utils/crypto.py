"""
Encryption utilities for securely storing user credentials.
Uses Fernet symmetric encryption.
"""
from cryptography.fernet import Fernet
from booking_bot.config import ENCRYPTION_KEY


def get_cipher():
    """Get or create a Fernet cipher."""
    if not ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not set in .env! Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    return Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_text(plain_text: str) -> str:
    """Encrypt a string and return base64-encoded ciphertext."""
    cipher = get_cipher()
    return cipher.encrypt(plain_text.encode()).decode()


def decrypt_text(encrypted_text: str) -> str:
    """Decrypt a base64-encoded ciphertext and return the original string."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_text.encode()).decode()
