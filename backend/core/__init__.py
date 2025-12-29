from backend.core.config import settings


# Lazy imports to avoid circular dependency
# auth imports db.session which imports core.config
def __getattr__(name):
    if name == "authenticate":
        from backend.core.auth import authenticate

        return authenticate
    elif name == "require_auth":
        from backend.core.auth import require_auth

        return require_auth
    elif name == "AppCredentials":
        from backend.core.auth import AppCredentials

        return AppCredentials
    elif name == "UsageContract":
        from backend.core.contracts import UsageContract

        return UsageContract
    elif name == "validate_contract":
        from backend.core.contracts import validate_contract

        return validate_contract
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "settings",
    "authenticate",
    "require_auth",
    "AppCredentials",
    "UsageContract",
    "validate_contract",
]
