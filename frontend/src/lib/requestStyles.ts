/**
 * Request Status Styles Utilities
 *
 * Centralized logic for determining request status and applying consistent styles
 * across the application (Analytics, Budget Details, etc.)
 */

export type RequestStatus = 'error' | 'success' | 'blocked';

/**
 * Determines the status of a request based on its properties
 */
export function getRequestStatus(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): RequestStatus {
  // Check error field (can be boolean or string with error message)
  if (request.error) {
    return 'error';
  }

  // Check blocked field
  if (request.blocked) {
    return 'blocked';
  }

  // Check status field
  if (request.status === 'error') {
    return 'error';
  }

  if (request.status === 'blocked') {
    return 'blocked';
  }

  // Default to success
  return 'success';
}

/**
 * Returns CSS class names for a request row based on its status
 */
export function getRequestRowClass(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): string {
  const status = getRequestStatus(request);
  const baseClass = 'border-t';

  switch (status) {
    case 'error':
      return `${baseClass} request-row-error`;
    case 'blocked':
      return `${baseClass} request-row-blocked`;
    case 'success':
    default:
      return `${baseClass} request-row-success`;
  }
}

/**
 * Returns CSS class names for primary text based on request status
 */
export function getRequestTextClass(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): string {
  const status = getRequestStatus(request);

  switch (status) {
    case 'error':
      return 'request-text-error';
    case 'blocked':
      return 'request-text-blocked';
    case 'success':
    default:
      return 'request-text-success';
  }
}

/**
 * Returns CSS class names for secondary text (e.g., token counts) based on request status
 */
export function getRequestSecondaryTextClass(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): string {
  const status = getRequestStatus(request);

  switch (status) {
    case 'error':
      return 'request-text-secondary-error';
    case 'blocked':
      return 'request-text-secondary-blocked';
    case 'success':
    default:
      return 'request-text-secondary-success';
  }
}

/**
 * Returns CSS class names for icons based on request status
 */
export function getRequestIconClass(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): string {
  const status = getRequestStatus(request);

  switch (status) {
    case 'error':
      return 'request-icon-error';
    case 'blocked':
      return 'request-icon-blocked';
    case 'success':
    default:
      return 'request-icon-success';
  }
}

/**
 * Returns CSS class names for code badges (e.g., model name) based on request status
 */
export function getRequestCodeClass(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): string {
  const status = getRequestStatus(request);

  switch (status) {
    case 'error':
      return 'text-sm px-2 py-1 rounded request-code-error';
    case 'blocked':
      return 'text-sm px-2 py-1 rounded request-code-blocked';
    case 'success':
    default:
      return 'text-sm px-2 py-1 rounded request-code-success';
  }
}

/**
 * Returns CSS class names for status badges based on request status
 */
export function getStatusBadgeClass(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): string {
  const status = getRequestStatus(request);

  switch (status) {
    case 'error':
      return 'status-badge-error';
    case 'blocked':
      return 'status-badge-blocked';
    case 'success':
    default:
      return 'status-badge-success';
  }
}

/**
 * Returns the display text for a status badge
 */
export function getStatusBadgeText(request: {
  error?: boolean | string | null;
  blocked?: boolean;
  status?: string;
}): string {
  const status = getRequestStatus(request);

  switch (status) {
    case 'error':
      return 'Error';
    case 'blocked':
      return 'Blocked';
    case 'success':
    default:
      return 'Success';
  }
}
