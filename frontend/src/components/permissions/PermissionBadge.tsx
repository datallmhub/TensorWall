'use client';

import { Shield, Lock, Eye, Users } from 'lucide-react';

/**
 * Permission Badge Component
 *
 * Displays a visual badge for roles and permissions
 */

interface PermissionBadgeProps {
  role: string;
  size?: 'sm' | 'md' | 'lg';
}

const ROLE_STYLES = {
  super_admin: {
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    border: 'border-purple-300',
    icon: Shield,
    label: 'Super Admin',
  },
  admin: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    border: 'border-blue-300',
    icon: Shield,
    label: 'Admin',
  },
  developer: {
    bg: 'bg-green-100',
    text: 'text-green-700',
    border: 'border-green-300',
    icon: Users,
    label: 'Developer',
  },
  analyst: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-700',
    border: 'border-yellow-300',
    icon: Eye,
    label: 'Analyst',
  },
  viewer: {
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    border: 'border-gray-300',
    icon: Lock,
    label: 'Viewer',
  },
};

const SIZE_CLASSES = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-2 text-base',
};

const ICON_SIZES = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

export function PermissionBadge({ role, size = 'md' }: PermissionBadgeProps) {
  const style = ROLE_STYLES[role as keyof typeof ROLE_STYLES] || ROLE_STYLES.viewer;
  const Icon = style.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${style.bg} ${style.text} ${style.border} ${SIZE_CLASSES[size]}`}
    >
      <Icon className={ICON_SIZES[size]} />
      {style.label}
    </span>
  );
}

/**
 * Permission List Component
 *
 * Displays a list of permission codes as badges
 */
interface PermissionListProps {
  permissions: string[];
  max?: number; // Max number to show before "+N more"
}

export function PermissionList({ permissions, max = 10 }: PermissionListProps) {
  const displayPermissions = max ? permissions.slice(0, max) : permissions;
  const remaining = max && permissions.length > max ? permissions.length - max : 0;

  return (
    <div className="flex flex-wrap gap-2">
      {displayPermissions.map((perm) => (
        <span
          key={perm}
          className="inline-flex items-center px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded border border-gray-300"
        >
          {perm}
        </span>
      ))}
      {remaining > 0 && (
        <span className="inline-flex items-center px-2 py-1 text-xs bg-gray-200 text-gray-600 rounded">
          +{remaining} more
        </span>
      )}
    </div>
  );
}

/**
 * Role Selector Component
 *
 * Dropdown to select a role (for admin interfaces)
 */
interface RoleSelectorProps {
  value: string;
  onChange: (role: string) => void;
  disabled?: boolean;
}

export function RoleSelector({ value, onChange, disabled = false }: RoleSelectorProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
    >
      <option value="">Select a role...</option>
      {Object.entries(ROLE_STYLES).map(([roleKey, roleStyle]) => (
        <option key={roleKey} value={roleKey}>
          {roleStyle.label}
        </option>
      ))}
    </select>
  );
}
