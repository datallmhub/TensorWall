"""In-Memory Encryption Adapter.

Architecture Hexagonale: Implémentation native du EncryptionPort
utilisant Fernet pour le chiffrement symétrique.

Cette implémentation fournit:
- Chiffrement Fernet (AES-128-CBC + HMAC-SHA256)
- Support de rotation de clés via MultiFernet
- Hachage SHA-256 pour les clés API gateway
- Dérivation de clé PBKDF2 optionnelle
"""

import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from backend.ports.encryption import EncryptionPort, KeyRotationStatus


class InMemoryEncryptionAdapter(EncryptionPort):
    """
    Native implementation of encryption using Fernet.

    Fernet provides:
    - AES-128-CBC encryption
    - HMAC-SHA256 authentication
    - Timestamp-based token format
    """

    def __init__(
        self,
        key: str | None = None,
        derive_from_secret: str | None = None,
        salt: str = "gateway-salt-v1",
    ):
        """
        Initialize encryption adapter.

        Args:
            key: Direct Fernet key (base64-encoded)
            derive_from_secret: Secret to derive key from using PBKDF2
            salt: Salt for key derivation
        """
        self._fernet: Fernet | None = None
        self._multi_fernet: MultiFernet | None = None
        self._rotation_in_progress = False
        self._old_key_valid = False

        if key:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        elif derive_from_secret:
            derived_key = self._derive_key(derive_from_secret, salt)
            self._fernet = Fernet(derived_key)
        else:
            # Generate a new key for testing
            self._fernet = Fernet(Fernet.generate_key())

    def _derive_key(self, secret: str, salt: str) -> bytes:
        """Derive a Fernet key from a secret using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(secret.encode()))

    # -------------------------------------------------------------------------
    # Core Encryption
    # -------------------------------------------------------------------------

    async def encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        encrypted = self._fernet.encrypt(plaintext.encode())
        return encrypted.decode()

    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        try:
            fernet = self._multi_fernet or self._fernet
            decrypted = fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            raise ValueError("Invalid encrypted data or wrong key")

    async def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt bytes."""
        return self._fernet.encrypt(data)

    async def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypt bytes."""
        try:
            fernet = self._multi_fernet or self._fernet
            return fernet.decrypt(encrypted_data)
        except InvalidToken:
            raise ValueError("Invalid encrypted data or wrong key")

    # -------------------------------------------------------------------------
    # API Key Encryption
    # -------------------------------------------------------------------------

    async def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key for storage."""
        return await self.encrypt(api_key)

    async def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt a stored API key."""
        return await self.decrypt(encrypted_key)

    # -------------------------------------------------------------------------
    # Hashing
    # -------------------------------------------------------------------------

    async def hash_key(self, key: str, salt: str | None = None) -> str:
        """Hash a key using SHA-256."""
        if salt:
            key = f"{salt}:{key}"
        return hashlib.sha256(key.encode()).hexdigest()

    async def verify_key_hash(
        self,
        key: str,
        hash_value: str,
        salt: str | None = None,
    ) -> bool:
        """Verify a key against its hash using constant-time comparison."""
        computed_hash = await self.hash_key(key, salt)
        return hmac.compare_digest(computed_hash, hash_value)

    # -------------------------------------------------------------------------
    # Key Rotation
    # -------------------------------------------------------------------------

    async def setup_key_rotation(self, old_key: str, new_key: str) -> None:
        """Configure key rotation with MultiFernet."""
        old_fernet = Fernet(old_key.encode())
        new_fernet = Fernet(new_key.encode())

        # New key first for encryption, both for decryption
        self._multi_fernet = MultiFernet([new_fernet, old_fernet])
        self._fernet = new_fernet
        self._rotation_in_progress = True
        self._old_key_valid = True

    async def rotate_encrypted_value(self, encrypted_data: str) -> str:
        """Re-encrypt data with the current key."""
        if not self._multi_fernet:
            return encrypted_data

        try:
            decrypted = self._multi_fernet.decrypt(encrypted_data.encode())
            return self._fernet.encrypt(decrypted).decode()
        except InvalidToken:
            raise ValueError("Failed to rotate encrypted value")

    async def get_rotation_status(self) -> KeyRotationStatus:
        """Get key rotation status."""
        return KeyRotationStatus(
            rotation_in_progress=self._rotation_in_progress,
            old_key_valid=self._old_key_valid,
            new_key_active=True,
        )

    async def complete_rotation(self) -> None:
        """Complete key rotation, disabling old key."""
        self._multi_fernet = None
        self._rotation_in_progress = False
        self._old_key_valid = False

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    async def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be Fernet-encrypted."""
        try:
            decoded = base64.urlsafe_b64decode(data.encode())
            # Fernet tokens start with version byte (0x80) and are at least 73 bytes
            return len(decoded) >= 73 and decoded[0] == 0x80
        except Exception:
            return False

    async def safe_decrypt(self, data: str) -> str | None:
        """Attempt to decrypt, returning None on failure."""
        try:
            return await self.decrypt(data)
        except (ValueError, InvalidToken):
            return None

    async def generate_key(self) -> str:
        """Generate a new Fernet key."""
        return Fernet.generate_key().decode()
