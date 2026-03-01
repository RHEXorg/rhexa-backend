# app/services/encryption.py
from cryptography.fernet import Fernet
from app.core.config import settings

class EncryptionService:
    def __init__(self):
        # We ensure the key is bytes and properly padded if it was just a string
        key = settings.ENCRYPTION_KEY
        if isinstance(key, str):
            key = key.encode()
        self.cipher = Fernet(key)
    
    def encrypt(self, plain_text: str) -> str:
        """Encrypts a plain text string to a base64 encoded string."""
        if not plain_text:
            return ""
        return self.cipher.encrypt(plain_text.encode()).decode()
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypts an encrypted string back to plain text."""
        if not encrypted_text:
            return ""
        return self.cipher.decrypt(encrypted_text.encode()).decode()

encryption_service = EncryptionService()
