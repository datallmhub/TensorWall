"""Unit tests for InMemoryEncryptionAdapter.

Tests couvrant:
- Chiffrement/déchiffrement de chaînes
- Chiffrement/déchiffrement de bytes
- Chiffrement de clés API
- Hachage et vérification
- Rotation de clés
- Méthodes utilitaires
"""

import pytest
from cryptography.fernet import Fernet

from backend.adapters.encryption.in_memory_adapter import InMemoryEncryptionAdapter


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def adapter():
    """Adapter avec clé générée."""
    return InMemoryEncryptionAdapter()


@pytest.fixture
def adapter_with_key():
    """Adapter avec clé spécifique."""
    key = Fernet.generate_key().decode()
    return InMemoryEncryptionAdapter(key=key)


@pytest.fixture
def adapter_from_secret():
    """Adapter avec clé dérivée d'un secret."""
    return InMemoryEncryptionAdapter(
        derive_from_secret="my-secret-password",
        salt="test-salt",
    )


# =============================================================================
# Tests: Core Encryption
# =============================================================================


class TestCoreEncryption:
    """Tests pour le chiffrement de base."""

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_string(self, adapter):
        """Chiffre et déchiffre une chaîne."""
        original = "Hello, World!"
        encrypted = await adapter.encrypt(original)

        assert encrypted != original
        assert len(encrypted) > len(original)

        decrypted = await adapter.decrypt(encrypted)
        assert decrypted == original

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_unicode(self, adapter):
        """Chiffre et déchiffre des caractères Unicode."""
        original = "Bonjour le monde! 🌍 中文 العربية"
        encrypted = await adapter.encrypt(original)
        decrypted = await adapter.decrypt(encrypted)

        assert decrypted == original

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_empty_string(self, adapter):
        """Chiffre et déchiffre une chaîne vide."""
        original = ""
        encrypted = await adapter.encrypt(original)
        decrypted = await adapter.decrypt(encrypted)

        assert decrypted == original

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_long_string(self, adapter):
        """Chiffre et déchiffre une longue chaîne."""
        original = "x" * 10000
        encrypted = await adapter.encrypt(original)
        decrypted = await adapter.decrypt(encrypted)

        assert decrypted == original

    @pytest.mark.asyncio
    async def test_decrypt_invalid_data(self, adapter):
        """Échoue sur données invalides."""
        with pytest.raises(ValueError, match="Invalid encrypted data"):
            await adapter.decrypt("not-encrypted-data")

    @pytest.mark.asyncio
    async def test_decrypt_wrong_key(self):
        """Échoue avec mauvaise clé."""
        adapter1 = InMemoryEncryptionAdapter()
        adapter2 = InMemoryEncryptionAdapter()

        encrypted = await adapter1.encrypt("secret")

        with pytest.raises(ValueError, match="Invalid encrypted data"):
            await adapter2.decrypt(encrypted)


# =============================================================================
# Tests: Bytes Encryption
# =============================================================================


class TestBytesEncryption:
    """Tests pour le chiffrement de bytes."""

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_bytes(self, adapter):
        """Chiffre et déchiffre des bytes."""
        original = b"Binary data \x00\x01\x02"
        encrypted = await adapter.encrypt_bytes(original)

        assert encrypted != original
        assert isinstance(encrypted, bytes)

        decrypted = await adapter.decrypt_bytes(encrypted)
        assert decrypted == original

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_empty_bytes(self, adapter):
        """Chiffre et déchiffre des bytes vides."""
        original = b""
        encrypted = await adapter.encrypt_bytes(original)
        decrypted = await adapter.decrypt_bytes(encrypted)

        assert decrypted == original


# =============================================================================
# Tests: API Key Encryption
# =============================================================================


class TestAPIKeyEncryption:
    """Tests pour le chiffrement de clés API."""

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_api_key(self, adapter):
        """Chiffre et déchiffre une clé API."""
        api_key = "sk-1234567890abcdef"
        encrypted = await adapter.encrypt_api_key(api_key)

        assert encrypted != api_key
        assert "sk-" not in encrypted

        decrypted = await adapter.decrypt_api_key(encrypted)
        assert decrypted == api_key

    @pytest.mark.asyncio
    async def test_encrypt_openai_key(self, adapter):
        """Chiffre une clé OpenAI."""
        api_key = "sk-proj-abc123def456ghi789"
        encrypted = await adapter.encrypt_api_key(api_key)
        decrypted = await adapter.decrypt_api_key(encrypted)

        assert decrypted == api_key

    @pytest.mark.asyncio
    async def test_encrypt_anthropic_key(self, adapter):
        """Chiffre une clé Anthropic."""
        api_key = "sk-ant-api03-abc123"
        encrypted = await adapter.encrypt_api_key(api_key)
        decrypted = await adapter.decrypt_api_key(encrypted)

        assert decrypted == api_key


# =============================================================================
# Tests: Hashing
# =============================================================================


class TestHashing:
    """Tests pour le hachage de clés."""

    @pytest.mark.asyncio
    async def test_hash_key(self, adapter):
        """Hache une clé."""
        key = "my-api-key"
        hash1 = await adapter.hash_key(key)

        assert len(hash1) == 64  # SHA-256 hex
        assert hash1 != key

    @pytest.mark.asyncio
    async def test_hash_key_deterministic(self, adapter):
        """Le hachage est déterministe."""
        key = "my-api-key"
        hash1 = await adapter.hash_key(key)
        hash2 = await adapter.hash_key(key)

        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_hash_key_with_salt(self, adapter):
        """Le sel modifie le hash."""
        key = "my-api-key"
        hash1 = await adapter.hash_key(key)
        hash2 = await adapter.hash_key(key, salt="custom-salt")

        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_verify_key_hash_valid(self, adapter):
        """Vérifie un hash valide."""
        key = "my-api-key"
        hash_value = await adapter.hash_key(key)

        result = await adapter.verify_key_hash(key, hash_value)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_key_hash_invalid(self, adapter):
        """Rejette un hash invalide."""
        key = "my-api-key"
        wrong_hash = "0" * 64

        result = await adapter.verify_key_hash(key, wrong_hash)
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_key_hash_with_salt(self, adapter):
        """Vérifie un hash avec sel."""
        key = "my-api-key"
        salt = "my-salt"
        hash_value = await adapter.hash_key(key, salt)

        result = await adapter.verify_key_hash(key, hash_value, salt)
        assert result is True


# =============================================================================
# Tests: Key Rotation
# =============================================================================


class TestKeyRotation:
    """Tests pour la rotation de clés."""

    @pytest.mark.asyncio
    async def test_setup_key_rotation(self):
        """Configure la rotation de clés."""
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        adapter = InMemoryEncryptionAdapter(key=old_key)

        # Chiffrer avec l'ancienne clé
        await adapter.encrypt("secret")

        # Configurer la rotation
        await adapter.setup_key_rotation(old_key, new_key)

        status = await adapter.get_rotation_status()
        assert status.rotation_in_progress is True
        assert status.old_key_valid is True

    @pytest.mark.asyncio
    async def test_decrypt_after_rotation(self):
        """Déchiffre avec les deux clés pendant rotation."""
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        adapter = InMemoryEncryptionAdapter(key=old_key)

        # Chiffrer avec l'ancienne clé
        encrypted_old = await adapter.encrypt("secret-old")

        # Configurer rotation
        await adapter.setup_key_rotation(old_key, new_key)

        # Chiffrer avec la nouvelle clé
        encrypted_new = await adapter.encrypt("secret-new")

        # Les deux doivent être déchiffrables
        decrypted_old = await adapter.decrypt(encrypted_old)
        decrypted_new = await adapter.decrypt(encrypted_new)

        assert decrypted_old == "secret-old"
        assert decrypted_new == "secret-new"

    @pytest.mark.asyncio
    async def test_rotate_encrypted_value(self):
        """Migre une valeur vers la nouvelle clé."""
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        adapter = InMemoryEncryptionAdapter(key=old_key)
        encrypted_old = await adapter.encrypt("secret")

        await adapter.setup_key_rotation(old_key, new_key)

        # Migrer vers nouvelle clé
        rotated = await adapter.rotate_encrypted_value(encrypted_old)

        # Doit être différent (nouveau token)
        assert rotated != encrypted_old

        # Doit toujours déchiffrer correctement
        decrypted = await adapter.decrypt(rotated)
        assert decrypted == "secret"

    @pytest.mark.asyncio
    async def test_complete_rotation(self):
        """Termine la rotation."""
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        adapter = InMemoryEncryptionAdapter(key=old_key)
        await adapter.setup_key_rotation(old_key, new_key)
        await adapter.complete_rotation()

        status = await adapter.get_rotation_status()
        assert status.rotation_in_progress is False
        assert status.old_key_valid is False


# =============================================================================
# Tests: Utility Methods
# =============================================================================


class TestUtilityMethods:
    """Tests pour les méthodes utilitaires."""

    @pytest.mark.asyncio
    async def test_is_encrypted_true(self, adapter):
        """Détecte les données chiffrées."""
        encrypted = await adapter.encrypt("secret")
        result = await adapter.is_encrypted(encrypted)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_encrypted_false(self, adapter):
        """Détecte les données non chiffrées."""
        result = await adapter.is_encrypted("not-encrypted")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_encrypted_empty(self, adapter):
        """Gère les chaînes vides."""
        result = await adapter.is_encrypted("")
        assert result is False

    @pytest.mark.asyncio
    async def test_safe_decrypt_success(self, adapter):
        """Déchiffre avec safe_decrypt."""
        encrypted = await adapter.encrypt("secret")
        result = await adapter.safe_decrypt(encrypted)

        assert result == "secret"

    @pytest.mark.asyncio
    async def test_safe_decrypt_failure(self, adapter):
        """Retourne None sur échec."""
        result = await adapter.safe_decrypt("not-encrypted")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_key(self, adapter):
        """Génère une nouvelle clé."""
        key = await adapter.generate_key()

        assert len(key) == 44  # Base64-encoded Fernet key
        # Vérifie que c'est une clé valide
        Fernet(key.encode())


# =============================================================================
# Tests: Key Derivation
# =============================================================================


class TestKeyDerivation:
    """Tests pour la dérivation de clés."""

    @pytest.mark.asyncio
    async def test_derived_key_works(self, adapter_from_secret):
        """La clé dérivée fonctionne."""
        encrypted = await adapter_from_secret.encrypt("secret")
        decrypted = await adapter_from_secret.decrypt(encrypted)

        assert decrypted == "secret"

    @pytest.mark.asyncio
    async def test_same_secret_same_key(self):
        """Le même secret donne la même clé."""
        adapter1 = InMemoryEncryptionAdapter(
            derive_from_secret="password",
            salt="salt",
        )
        adapter2 = InMemoryEncryptionAdapter(
            derive_from_secret="password",
            salt="salt",
        )

        encrypted = await adapter1.encrypt("secret")
        decrypted = await adapter2.decrypt(encrypted)

        assert decrypted == "secret"

    @pytest.mark.asyncio
    async def test_different_salt_different_key(self):
        """Des sels différents donnent des clés différentes."""
        adapter1 = InMemoryEncryptionAdapter(
            derive_from_secret="password",
            salt="salt1",
        )
        adapter2 = InMemoryEncryptionAdapter(
            derive_from_secret="password",
            salt="salt2",
        )

        encrypted = await adapter1.encrypt("secret")

        with pytest.raises(ValueError):
            await adapter2.decrypt(encrypted)
