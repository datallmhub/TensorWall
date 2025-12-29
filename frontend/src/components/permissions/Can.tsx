'use client';

import { ReactNode } from 'react';
import { usePermissions } from '@/contexts/PermissionContext';

/**
 * Can Component - Conditional rendering based on permissions
 *
 * Shows children only if user has the required permission
 *
 * Examples:
 *   <Can resource="budgets" action="create">
 *     <button>Create Budget</button>
 *   </Can>
 *
 *   <Can resource="budgets" action="delete" fallback={<p>No access</p>}>
 *     <button>Delete Budget</button>
 *   </Can>
 */

interface CanProps {
  resource: string;
  action: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function Can({ resource, action, children, fallback = null }: CanProps) {
  const { hasPermission, loading } = usePermissions();

  if (loading) {
    return fallback;
  }

  if (!hasPermission(resource, action)) {
    return fallback;
  }

  return <>{children}</>;
}

/**
 * CanAny Component - Shows content if user has ANY of the specified permissions
 */
interface CanAnyProps {
  permissions: Array<[string, string]>; // Array of [resource, action] tuples
  children: ReactNode;
  fallback?: ReactNode;
}

export function CanAny({ permissions, children, fallback = null }: CanAnyProps) {
  const { hasAnyPermission, loading } = usePermissions();

  if (loading) {
    return fallback;
  }

  if (!hasAnyPermission(permissions)) {
    return fallback;
  }

  return <>{children}</>;
}

/**
 * HasRole Component - Shows content if user has the specified role
 */
interface HasRoleProps {
  role: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function HasRole({ role, children, fallback = null }: HasRoleProps) {
  const { hasRole, loading } = usePermissions();

  if (loading) {
    return fallback;
  }

  if (!hasRole(role)) {
    return fallback;
  }

  return <>{children}</>;
}

/**
 * HasAnyRole Component - Shows content if user has ANY of the specified roles
 */
interface HasAnyRoleProps {
  roles: string[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function HasAnyRole({ roles, children, fallback = null }: HasAnyRoleProps) {
  const { hasAnyRole, loading } = usePermissions();

  if (loading) {
    return fallback;
  }

  if (!hasAnyRole(roles)) {
    return fallback;
  }

  return <>{children}</>;
}
