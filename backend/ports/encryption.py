"""Encryption Port - Interface Abstraite.

Architecture Hexagonale: Port pour le chiffrement des données sensibles.

Fonctionnalités:
- Chiffrement/déchiffrement de chaînes et bytes
- Chiffrement spécifique pour les clés API
- Hachage de clés (pour vérification sans déchiffrement)
- Support de rotation de clés
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class KeyRotationStatus:
    """Statut de la rotation de clés."""

    rotation_in_progress: bool
    old_key_valid: bool
    new_key_active: bool
    migrated_count: int = 0
    pending_count: int = 0


class EncryptionPort(ABC):
    """
    Port abstrait pour le chiffrement.

    Interface que les adapters doivent implémenter pour fournir
    des fonctionnalités de chiffrement sécurisé.
    """

    # -------------------------------------------------------------------------
    # Core Encryption
    # -------------------------------------------------------------------------

    @abstractmethod
    async def encrypt(self, plaintext: str) -> str:
        """
        Chiffre une chaîne de caractères.

        Args:
            plaintext: Texte en clair à chiffrer

        Returns:
            Texte chiffré encodé en base64
        """
        ...

    @abstractmethod
    async def decrypt(self, ciphertext: str) -> str:
        """
        Déchiffre une chaîne chiffrée.

        Args:
            ciphertext: Texte chiffré encodé en base64

        Returns:
            Texte en clair original

        Raises:
            ValueError: Si le déchiffrement échoue
        """
        ...

    @abstractmethod
    async def encrypt_bytes(self, data: bytes) -> bytes:
        """
        Chiffre des données binaires.

        Args:
            data: Données binaires à chiffrer

        Returns:
            Données chiffrées
        """
        ...

    @abstractmethod
    async def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """
        Déchiffre des données binaires.

        Args:
            encrypted_data: Données chiffrées

        Returns:
            Données binaires originales

        Raises:
            ValueError: Si le déchiffrement échoue
        """
        ...

    # -------------------------------------------------------------------------
    # API Key Encryption
    # -------------------------------------------------------------------------

    @abstractmethod
    async def encrypt_api_key(self, api_key: str) -> str:
        """
        Chiffre une clé API pour stockage sécurisé.

        Args:
            api_key: Clé API en clair (OpenAI, Anthropic, etc.)

        Returns:
            Clé API chiffrée
        """
        ...

    @abstractmethod
    async def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Déchiffre une clé API stockée.

        Args:
            encrypted_key: Clé API chiffrée

        Returns:
            Clé API en clair
        """
        ...

    # -------------------------------------------------------------------------
    # Hashing
    # -------------------------------------------------------------------------

    @abstractmethod
    async def hash_key(self, key: str, salt: str | None = None) -> str:
        """
        Hache une clé (pour vérification sans déchiffrement).

        Utilisé pour les clés API gateway où on vérifie
        sans avoir besoin de récupérer la clé originale.

        Args:
            key: Clé à hacher
            salt: Sel optionnel pour le hachage

        Returns:
            Hash de la clé (hex)
        """
        ...

    @abstractmethod
    async def verify_key_hash(
        self,
        key: str,
        hash_value: str,
        salt: str | None = None,
    ) -> bool:
        """
        Vérifie qu'une clé correspond à son hash.

        Utilise une comparaison à temps constant pour éviter
        les attaques par timing.

        Args:
            key: Clé à vérifier
            hash_value: Hash attendu
            salt: Sel utilisé lors du hachage

        Returns:
            True si la clé correspond au hash
        """
        ...

    # -------------------------------------------------------------------------
    # Key Rotation
    # -------------------------------------------------------------------------

    @abstractmethod
    async def setup_key_rotation(self, old_key: str, new_key: str) -> None:
        """
        Configure la rotation de clés.

        Pendant la rotation:
        1. Les nouveaux chiffrements utilisent la nouvelle clé
        2. Les déchiffrements essaient la nouvelle clé, puis l'ancienne
        3. Les données doivent être re-chiffrées pour migrer

        Args:
            old_key: Ancienne clé de chiffrement
            new_key: Nouvelle clé de chiffrement
        """
        ...

    @abstractmethod
    async def rotate_encrypted_value(self, encrypted_data: str) -> str:
        """
        Re-chiffre une valeur avec la clé actuelle.

        Utilisé pendant la rotation pour migrer les données.

        Args:
            encrypted_data: Données chiffrées avec ancienne ou nouvelle clé

        Returns:
            Données re-chiffrées avec la clé actuelle
        """
        ...

    @abstractmethod
    async def get_rotation_status(self) -> KeyRotationStatus:
        """
        Obtient le statut de la rotation de clés.

        Returns:
            Statut actuel de la rotation
        """
        ...

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    @abstractmethod
    async def is_encrypted(self, data: str) -> bool:
        """
        Vérifie si des données semblent être chiffrées.

        Note: C'est une heuristique, pas une garantie.

        Args:
            data: Données à vérifier

        Returns:
            True si les données semblent chiffrées
        """
        ...

    @abstractmethod
    async def safe_decrypt(self, data: str) -> str | None:
        """
        Tente de déchiffrer, retourne None en cas d'échec.

        Utile pour gérer des données potentiellement non chiffrées.

        Args:
            data: Données à déchiffrer

        Returns:
            Données déchiffrées ou None si échec
        """
        ...

    @abstractmethod
    async def generate_key(self) -> str:
        """
        Génère une nouvelle clé de chiffrement.

        Returns:
            Nouvelle clé encodée en base64
        """
        ...
