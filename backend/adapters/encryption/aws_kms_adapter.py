"""AWS KMS Encryption Adapter.

Architecture Hexagonale: Implémentation production du EncryptionPort
utilisant AWS Key Management Service pour le chiffrement.

Ce module fournit:
- Chiffrement/déchiffrement via AWS KMS
- Envelope encryption pour les données volumineuses
- Support de rotation de clés via alias
- Caching des data keys pour performance
"""

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet

from backend.ports.encryption import EncryptionPort, KeyRotationStatus


class AWSKMSEncryptionAdapter(EncryptionPort):
    """
    AWS KMS implementation of encryption.

    Uses envelope encryption:
    1. KMS generates/encrypts a data key
    2. Data key is used locally for Fernet encryption
    3. Encrypted data key is stored with the ciphertext

    This approach:
    - Minimizes KMS API calls
    - Allows encryption of large data
    - Provides key rotation via KMS aliases
    """

    def __init__(
        self,
        kms_key_id: str | None = None,
        region: str = "us-east-1",
        cache_ttl_seconds: int = 300,
        boto_client: Any = None,
    ):
        """
        Initialize AWS KMS adapter.

        Args:
            kms_key_id: KMS key ID, ARN, or alias (e.g., 'alias/my-key')
            region: AWS region
            cache_ttl_seconds: How long to cache data keys
            boto_client: Optional boto3 KMS client (for testing)
        """
        self._kms_key_id = kms_key_id or os.environ.get("AWS_KMS_KEY_ID", "alias/tensorwall")
        self._region = region
        self._cache_ttl = cache_ttl_seconds
        self._kms_client = boto_client

        # Cached data key for envelope encryption
        self._cached_data_key: bytes | None = None
        self._cached_encrypted_key: bytes | None = None
        self._cache_expires: datetime | None = None
        self._fernet: Fernet | None = None

        # Key rotation state
        self._rotation_in_progress = False
        self._old_key_id: str | None = None

    def _get_kms_client(self):
        """Get or create KMS client."""
        if self._kms_client:
            return self._kms_client

        try:
            import boto3

            self._kms_client = boto3.client("kms", region_name=self._region)
            return self._kms_client
        except ImportError:
            raise RuntimeError(
                "boto3 is required for AWS KMS adapter. Install with: pip install boto3"
            )

    async def _get_data_key(self) -> tuple[bytes, bytes]:
        """Get or generate a data key for envelope encryption."""
        now = datetime.now()

        # Return cached key if valid
        if self._cached_data_key and self._cache_expires and now < self._cache_expires:
            return self._cached_data_key, self._cached_encrypted_key

        # Generate new data key from KMS
        client = self._get_kms_client()
        response = client.generate_data_key(
            KeyId=self._kms_key_id,
            KeySpec="AES_256",
        )

        plaintext_key = response["Plaintext"]
        encrypted_key = response["CiphertextBlob"]

        # Cache the key
        self._cached_data_key = plaintext_key
        self._cached_encrypted_key = encrypted_key
        self._cache_expires = now + timedelta(seconds=self._cache_ttl)

        # Create Fernet with the data key
        fernet_key = base64.urlsafe_b64encode(plaintext_key[:32])
        self._fernet = Fernet(fernet_key)

        return plaintext_key, encrypted_key

    async def _decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt a data key using KMS."""
        client = self._get_kms_client()
        response = client.decrypt(
            CiphertextBlob=encrypted_key,
            KeyId=self._kms_key_id,
        )
        return response["Plaintext"]

    # -------------------------------------------------------------------------
    # Core Encryption
    # -------------------------------------------------------------------------

    async def encrypt(self, plaintext: str) -> str:
        """
        Encrypt using envelope encryption.

        Output format: base64(encrypted_data_key + fernet_token)
        """
        _, encrypted_key = await self._get_data_key()

        # Encrypt with Fernet (uses cached data key)
        fernet_token = self._fernet.encrypt(plaintext.encode())

        # Combine encrypted data key with ciphertext
        combined = len(encrypted_key).to_bytes(4, "big") + encrypted_key + fernet_token

        return base64.urlsafe_b64encode(combined).decode()

    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt envelope-encrypted data."""
        try:
            combined = base64.urlsafe_b64decode(ciphertext.encode())

            # Extract encrypted data key length and key
            key_length = int.from_bytes(combined[:4], "big")
            encrypted_key = combined[4 : 4 + key_length]
            fernet_token = combined[4 + key_length :]

            # Decrypt data key
            data_key = await self._decrypt_data_key(encrypted_key)

            # Create Fernet and decrypt
            fernet_key = base64.urlsafe_b64encode(data_key[:32])
            fernet = Fernet(fernet_key)

            return fernet.decrypt(fernet_token).decode()

        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    async def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt bytes using envelope encryption."""
        _, encrypted_key = await self._get_data_key()

        fernet_token = self._fernet.encrypt(data)
        combined = len(encrypted_key).to_bytes(4, "big") + encrypted_key + fernet_token

        return combined

    async def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypt bytes."""
        try:
            key_length = int.from_bytes(encrypted_data[:4], "big")
            encrypted_key = encrypted_data[4 : 4 + key_length]
            fernet_token = encrypted_data[4 + key_length :]

            data_key = await self._decrypt_data_key(encrypted_key)
            fernet_key = base64.urlsafe_b64encode(data_key[:32])
            fernet = Fernet(fernet_key)

            return fernet.decrypt(fernet_token)

        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    # -------------------------------------------------------------------------
    # API Key Encryption
    # -------------------------------------------------------------------------

    async def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key."""
        return await self.encrypt(api_key)

    async def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key."""
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
        """Verify a key against its hash."""
        computed_hash = await self.hash_key(key, salt)
        return hmac.compare_digest(computed_hash, hash_value)

    # -------------------------------------------------------------------------
    # Key Rotation
    # -------------------------------------------------------------------------

    async def setup_key_rotation(self, old_key: str, new_key: str) -> None:
        """
        Setup key rotation.

        For KMS, rotation is handled via key aliases:
        - old_key: Previous KMS key ID/alias
        - new_key: New KMS key ID/alias

        New encryptions use new key, decryptions try both.
        """
        self._old_key_id = old_key
        self._kms_key_id = new_key
        self._rotation_in_progress = True

        # Clear cache to force new key usage
        self._cached_data_key = None
        self._cached_encrypted_key = None
        self._cache_expires = None
        self._fernet = None

    async def rotate_encrypted_value(self, encrypted_data: str) -> str:
        """Re-encrypt data with the current key."""
        # Decrypt with old or new key
        plaintext = await self.decrypt(encrypted_data)

        # Re-encrypt with current key
        return await self.encrypt(plaintext)

    async def get_rotation_status(self) -> KeyRotationStatus:
        """Get key rotation status."""
        return KeyRotationStatus(
            rotation_in_progress=self._rotation_in_progress,
            old_key_valid=self._old_key_id is not None,
            new_key_active=True,
        )

    async def complete_rotation(self) -> None:
        """Complete key rotation."""
        self._rotation_in_progress = False
        self._old_key_id = None

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    async def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be envelope-encrypted."""
        try:
            decoded = base64.urlsafe_b64decode(data.encode())
            # Check minimum size: 4 bytes length + some key + some data
            if len(decoded) < 100:
                return False
            key_length = int.from_bytes(decoded[:4], "big")
            # Reasonable key length check
            return 100 <= key_length <= 500
        except Exception:
            return False

    async def safe_decrypt(self, data: str) -> str | None:
        """Attempt to decrypt, returning None on failure."""
        try:
            return await self.decrypt(data)
        except ValueError:
            return None

    async def generate_key(self) -> str:
        """
        Generate a new data key.

        Note: For KMS, this returns a new plaintext data key
        that can be used with Fernet locally.
        """
        client = self._get_kms_client()
        response = client.generate_data_key(
            KeyId=self._kms_key_id,
            KeySpec="AES_256",
        )
        return base64.urlsafe_b64encode(response["Plaintext"]).decode()

    def invalidate_cache(self) -> None:
        """Invalidate the data key cache."""
        self._cached_data_key = None
        self._cached_encrypted_key = None
        self._cache_expires = None
        self._fernet = None
