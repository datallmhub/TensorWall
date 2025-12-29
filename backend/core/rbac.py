"""Role-Based Access Control (RBAC) for TensorWall.

Defines roles, permissions, and access control logic.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Permission(str, Enum):
    """Available permissions in the system."""

    # Application management
    APPS_READ = "apps:read"
    APPS_WRITE = "apps:write"
    APPS_DELETE = "apps:delete"

    # API Key management
    KEYS_READ = "keys:read"
    KEYS_WRITE = "keys:write"
    KEYS_ROTATE = "keys:rotate"
    KEYS_DELETE = "keys:delete"

    # Policy management
    POLICIES_READ = "policies:read"
    POLICIES_WRITE = "policies:write"
    POLICIES_DELETE = "policies:delete"

    # Budget management
    BUDGETS_READ = "budgets:read"
    BUDGETS_WRITE = "budgets:write"
    BUDGETS_RESET = "budgets:reset"

    # Analytics & Audit
    ANALYTICS_READ = "analytics:read"
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # LLM API access
    LLM_CHAT = "llm:chat"
    LLM_EMBEDDINGS = "llm:embeddings"

    # Admin
    ADMIN_FULL = "admin:full"


class Role(str, Enum):
    """Predefined roles with associated permissions."""

    # Full access - platform owner
    OWNER = "owner"

    # Administrative access - can manage apps, policies, budgets
    ADMIN = "admin"

    # Security team - read audit, manage policies
    SECURITY = "security"

    # Finance team - read budgets and analytics
    FINANCE = "finance"

    # Auditor - read-only access to analytics and audit logs (for compliance)
    AUDITOR = "auditor"

    # Developer - use LLM APIs, read own app data
    DEVELOPER = "developer"

    # Read-only - view only
    VIEWER = "viewer"

    # Service account - LLM API only
    SERVICE = "service"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OWNER: set(Permission),  # All permissions
    Role.ADMIN: {
        Permission.APPS_READ,
        Permission.APPS_WRITE,
        Permission.APPS_DELETE,
        Permission.KEYS_READ,
        Permission.KEYS_WRITE,
        Permission.KEYS_ROTATE,
        Permission.KEYS_DELETE,
        Permission.POLICIES_READ,
        Permission.POLICIES_WRITE,
        Permission.POLICIES_DELETE,
        Permission.BUDGETS_READ,
        Permission.BUDGETS_WRITE,
        Permission.BUDGETS_RESET,
        Permission.ANALYTICS_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.LLM_CHAT,
        Permission.LLM_EMBEDDINGS,
    },
    Role.SECURITY: {
        Permission.APPS_READ,
        Permission.KEYS_READ,
        Permission.POLICIES_READ,
        Permission.POLICIES_WRITE,
        Permission.POLICIES_DELETE,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.ANALYTICS_READ,
    },
    Role.FINANCE: {
        Permission.APPS_READ,
        Permission.BUDGETS_READ,
        Permission.BUDGETS_WRITE,
        Permission.ANALYTICS_READ,
        Permission.AUDIT_READ,
    },
    # Auditor: read-only access for compliance and external auditors
    Role.AUDITOR: {
        Permission.APPS_READ,
        Permission.KEYS_READ,
        Permission.POLICIES_READ,
        Permission.BUDGETS_READ,
        Permission.ANALYTICS_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
    },
    Role.DEVELOPER: {
        Permission.APPS_READ,
        Permission.KEYS_READ,
        Permission.POLICIES_READ,
        Permission.BUDGETS_READ,
        Permission.ANALYTICS_READ,
        Permission.LLM_CHAT,
        Permission.LLM_EMBEDDINGS,
    },
    Role.VIEWER: {
        Permission.APPS_READ,
        Permission.KEYS_READ,
        Permission.POLICIES_READ,
        Permission.BUDGETS_READ,
        Permission.ANALYTICS_READ,
    },
    Role.SERVICE: {
        Permission.LLM_CHAT,
        Permission.LLM_EMBEDDINGS,
    },
}


class RBACContext(BaseModel):
    """Context for RBAC evaluation."""

    user_id: Optional[str] = None
    role: Role
    app_id: Optional[str] = None  # Scope to specific app
    additional_permissions: set[Permission] = set()  # Extra permissions granted
    denied_permissions: set[Permission] = set()  # Explicitly denied permissions


class RBACResult(BaseModel):
    """Result of permission check."""

    allowed: bool
    permission: str
    role: str
    reason: Optional[str] = None


class RBACEngine:
    """
    RBAC Engine for permission checking.

    Evaluates permissions based on role and context.
    """

    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS

    def has_permission(
        self,
        context: RBACContext,
        permission: Permission,
        resource_app_id: Optional[str] = None,
    ) -> RBACResult:
        """
        Check if the context has a specific permission.

        Args:
            context: RBAC context (role, user, app scope)
            permission: Permission to check
            resource_app_id: App ID of the resource being accessed

        Returns:
            RBACResult with allowed status and reason
        """
        # Check explicitly denied permissions first
        if permission in context.denied_permissions:
            return RBACResult(
                allowed=False,
                permission=permission.value,
                role=context.role.value,
                reason="Permission explicitly denied",
            )

        # Check additional granted permissions
        if permission in context.additional_permissions:
            return RBACResult(
                allowed=True,
                permission=permission.value,
                role=context.role.value,
                reason="Permission explicitly granted",
            )

        # Get role permissions
        role_perms = self.role_permissions.get(context.role, set())

        # Check if role has permission
        if permission not in role_perms:
            return RBACResult(
                allowed=False,
                permission=permission.value,
                role=context.role.value,
                reason=f"Role '{context.role.value}' does not have permission '{permission.value}'",
            )

        # Check app scope (if context is scoped to an app)
        if context.app_id and resource_app_id:
            if context.app_id != resource_app_id:
                # Allow if user has admin-level access
                if Permission.ADMIN_FULL not in role_perms:
                    return RBACResult(
                        allowed=False,
                        permission=permission.value,
                        role=context.role.value,
                        reason=f"Access denied: scoped to app '{context.app_id}', not '{resource_app_id}'",
                    )

        return RBACResult(
            allowed=True,
            permission=permission.value,
            role=context.role.value,
        )

    def has_any_permission(
        self,
        context: RBACContext,
        permissions: list[Permission],
        resource_app_id: Optional[str] = None,
    ) -> RBACResult:
        """Check if context has any of the given permissions."""
        for perm in permissions:
            result = self.has_permission(context, perm, resource_app_id)
            if result.allowed:
                return result

        return RBACResult(
            allowed=False,
            permission=",".join(p.value for p in permissions),
            role=context.role.value,
            reason="None of the required permissions are granted",
        )

    def has_all_permissions(
        self,
        context: RBACContext,
        permissions: list[Permission],
        resource_app_id: Optional[str] = None,
    ) -> RBACResult:
        """Check if context has all of the given permissions."""
        for perm in permissions:
            result = self.has_permission(context, perm, resource_app_id)
            if not result.allowed:
                return result

        return RBACResult(
            allowed=True,
            permission=",".join(p.value for p in permissions),
            role=context.role.value,
        )

    def get_role_permissions(self, role: Role) -> set[Permission]:
        """Get all permissions for a role."""
        return self.role_permissions.get(role, set())

    def list_roles(self) -> list[dict]:
        """List all roles with their permissions."""
        return [
            {
                "role": role.value,
                "permissions": [p.value for p in perms],
            }
            for role, perms in self.role_permissions.items()
        ]


# Singleton instance
rbac_engine = RBACEngine()


# Helper functions for common checks
def require_permission(
    context: RBACContext,
    permission: Permission,
    resource_app_id: Optional[str] = None,
) -> None:
    """
    Require a permission, raise exception if not allowed.

    Usage:
        require_permission(context, Permission.APPS_WRITE)
    """
    from fastapi import HTTPException

    result = rbac_engine.has_permission(context, permission, resource_app_id)
    if not result.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "permission_denied",
                "permission": result.permission,
                "role": result.role,
                "reason": result.reason,
            },
        )


def check_permission(
    context: RBACContext,
    permission: Permission,
    resource_app_id: Optional[str] = None,
) -> bool:
    """
    Check a permission without raising exception.

    Usage:
        if check_permission(context, Permission.BUDGETS_WRITE):
            # do something
    """
    result = rbac_engine.has_permission(context, permission, resource_app_id)
    return result.allowed
