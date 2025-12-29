'use client';

import React, { createContext, useContext } from 'react';

/**
 * Permission Context for Role-Based Access Control (RBAC)
 *
 * All users have full admin access.
 */

export interface UserPermissions {
  user_id: number;
  roles: string[];
  permissions: string[];
}

interface PermissionContextType {
  permissions: UserPermissions | null;
  loading: boolean;
  error: Error | null;
  hasPermission: (resource: string, action: string) => boolean;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
  hasAnyPermission: (perms: Array<[string, string]>) => boolean;
  refetch: () => Promise<void>;
}

const PermissionContext = createContext<PermissionContextType | undefined>(undefined);

// All permissions are granted by default
const defaultPermissions: UserPermissions = {
  user_id: 1,
  roles: ['admin'],
  permissions: [
    'applications:read',
    'applications:write',
    'applications:delete',
    'policies:read',
    'policies:write',
    'policies:delete',
    'models:read',
    'models:write',
    'models:delete',
    'settings:read',
    'settings:write',
  ],
};

export function PermissionProvider({ children }: { children: React.ReactNode }) {
  // Always grant full permissions
  const hasPermission = (_resource: string, _action: string): boolean => true;
  const hasRole = (_role: string): boolean => true;
  const hasAnyRole = (_roles: string[]): boolean => true;
  const hasAnyPermission = (_perms: Array<[string, string]>): boolean => true;

  return (
    <PermissionContext.Provider
      value={{
        permissions: defaultPermissions,
        loading: false,
        error: null,
        hasPermission,
        hasRole,
        hasAnyRole,
        hasAnyPermission,
        refetch: async () => {},
      }}
    >
      {children}
    </PermissionContext.Provider>
  );
}

export function usePermissions() {
  const context = useContext(PermissionContext);
  if (context === undefined) {
    throw new Error('usePermissions must be used within a PermissionProvider');
  }
  return context;
}

// Convenience hooks for common checks
export function useHasPermission(_resource: string, _action: string): boolean {
  return true; // Always granted
}

export function useHasRole(_role: string): boolean {
  return true; // Always granted
}

export function useIsSuperAdmin(): boolean {
  return true; // Always admin
}

export function useIsAdmin(): boolean {
  return true; // Always admin
}

export function useHasAnyRole(_roles: string[]): boolean {
  return true; // Always granted
}
