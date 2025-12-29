from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ActionType(str, Enum):
    GENERATE = "generate"
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    TRANSLATE = "translate"
    EMBED = "embed"
    OTHER = "other"


class UsageContract(BaseModel):
    """
    Contrat d'usage obligatoire pour chaque appel LLM.
    Refus si incomplet.
    """

    app_id: str = Field(..., description="Identifiant unique de l'application")
    feature: str = Field(..., description="Fonctionnalité / use-case")
    action: ActionType = Field(..., description="Type d'action LLM")
    environment: Environment = Field(..., description="Environnement d'exécution")
    owner: Optional[str] = Field(None, description="Équipe/service responsable")
    request_id: Optional[str] = Field(None, description="ID de requête pour traçabilité")

    class Config:
        json_schema_extra = {
            "example": {
                "app_id": "myapp-backend",
                "feature": "customer-support-bot",
                "action": "generate",
                "environment": "production",
                "owner": "team-platform",
                "request_id": "req_abc123",
            }
        }


class ContractValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


def validate_contract(contract: Optional[UsageContract]) -> ContractValidationResult:
    """Valide un contrat d'usage."""
    if contract is None:
        return ContractValidationResult(
            valid=False,
            errors=[
                "Usage contract is required. Provide X-LLM-Contract header or 'contract' field."
            ],
        )

    errors = []
    warnings = []

    # Validations
    if not contract.app_id or len(contract.app_id) < 3:
        errors.append("app_id must be at least 3 characters")

    if not contract.feature or len(contract.feature) < 2:
        errors.append("feature must be at least 2 characters")

    if contract.environment == Environment.PRODUCTION and not contract.owner:
        warnings.append("owner is recommended for production environments")

    return ContractValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
