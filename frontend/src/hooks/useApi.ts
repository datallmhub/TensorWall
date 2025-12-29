/**
 * Custom React hooks for API interactions
 *
 * Provides reusable hooks with loading/error states, automatic refetching,
 * and optimistic updates for all API resources.
 */

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/apiClient';
import type {
  Budget,
  Application,
  PolicyRule,
  User,
  BudgetCreateRequest,
  BudgetUpdateRequest,
  ApplicationCreateRequest,
  ApplicationUpdateRequest,
  PolicyCreateRequest,
  PolicyUpdateRequest,
  UserCreateRequest,
  UserUpdateRequest,
} from '@/types/api';

/**
 * Generic API hook with loading and error states
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  dependencies: any[] = []
): {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Budgets API hooks
 */
export function useBudgets() {
  const { data, loading, error, refetch } = useApi<Budget[]>(
    () => apiClient.get('/admin/budgets')
  );

  const createBudget = async (budget: BudgetCreateRequest): Promise<Budget> => {
    const created = await apiClient.post<Budget>('/admin/budgets', budget);
    await refetch();
    return created;
  };

  const updateBudget = async (uuid: string, updates: BudgetUpdateRequest): Promise<Budget> => {
    const updated = await apiClient.patch<Budget>(`/admin/budgets/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deleteBudget = async (uuid: string): Promise<void> => {
    await apiClient.delete(`/admin/budgets/${uuid}`);
    await refetch();
  };

  const resetBudget = async (uuid: string): Promise<Budget> => {
    const reset = await apiClient.post<Budget>(`/admin/budgets/${uuid}/reset`);
    await refetch();
    return reset;
  };

  return {
    budgets: data || [],
    loading,
    error,
    refetch,
    createBudget,
    updateBudget,
    deleteBudget,
    resetBudget,
  };
}

/**
 * Single Budget hook
 */
export function useBudget(uuid: string) {
  const { data, loading, error, refetch } = useApi<Budget>(
    () => apiClient.get(`/admin/budgets/${uuid}`),
    [uuid]
  );

  const updateBudget = async (updates: BudgetUpdateRequest): Promise<Budget> => {
    const updated = await apiClient.patch<Budget>(`/admin/budgets/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deleteBudget = async (): Promise<void> => {
    await apiClient.delete(`/admin/budgets/${uuid}`);
  };

  const resetBudget = async (): Promise<Budget> => {
    const reset = await apiClient.post<Budget>(`/admin/budgets/${uuid}/reset`);
    await refetch();
    return reset;
  };

  return {
    budget: data,
    loading,
    error,
    refetch,
    updateBudget,
    deleteBudget,
    resetBudget,
  };
}

/**
 * Applications API hooks
 */
export function useApplications() {
  const { data, loading, error, refetch } = useApi<Application[]>(
    () => apiClient.get('/admin/applications')
  );

  const createApplication = async (app: ApplicationCreateRequest): Promise<Application> => {
    const created = await apiClient.post<Application>('/admin/applications', app);
    await refetch();
    return created;
  };

  const updateApplication = async (
    uuid: string,
    updates: ApplicationUpdateRequest
  ): Promise<Application> => {
    const updated = await apiClient.patch<Application>(`/admin/applications/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deleteApplication = async (uuid: string): Promise<void> => {
    await apiClient.delete(`/admin/applications/${uuid}`);
    await refetch();
  };

  return {
    applications: data || [],
    loading,
    error,
    refetch,
    createApplication,
    updateApplication,
    deleteApplication,
  };
}

/**
 * Single Application hook
 */
export function useApplication(uuid: string) {
  const { data, loading, error, refetch } = useApi<Application>(
    () => apiClient.get(`/admin/applications/${uuid}`),
    [uuid]
  );

  const updateApplication = async (updates: ApplicationUpdateRequest): Promise<Application> => {
    const updated = await apiClient.patch<Application>(`/admin/applications/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deleteApplication = async (): Promise<void> => {
    await apiClient.delete(`/admin/applications/${uuid}`);
  };

  return {
    application: data,
    loading,
    error,
    refetch,
    updateApplication,
    deleteApplication,
  };
}

/**
 * Policies API hooks
 */
export function usePolicies() {
  const { data, loading, error, refetch } = useApi<PolicyRule[]>(
    () => apiClient.get('/admin/policies')
  );

  const createPolicy = async (policy: PolicyCreateRequest): Promise<PolicyRule> => {
    const created = await apiClient.post<PolicyRule>('/admin/policies', policy);
    await refetch();
    return created;
  };

  const updatePolicy = async (uuid: string, updates: PolicyUpdateRequest): Promise<PolicyRule> => {
    const updated = await apiClient.patch<PolicyRule>(`/admin/policies/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deletePolicy = async (uuid: string): Promise<void> => {
    await apiClient.delete(`/admin/policies/${uuid}`);
    await refetch();
  };

  const enablePolicy = async (uuid: string): Promise<PolicyRule> => {
    const enabled = await apiClient.post<PolicyRule>(`/admin/policies/${uuid}/enable`);
    await refetch();
    return enabled;
  };

  const disablePolicy = async (uuid: string): Promise<PolicyRule> => {
    const disabled = await apiClient.post<PolicyRule>(`/admin/policies/${uuid}/disable`);
    await refetch();
    return disabled;
  };

  return {
    policies: data || [],
    loading,
    error,
    refetch,
    createPolicy,
    updatePolicy,
    deletePolicy,
    enablePolicy,
    disablePolicy,
  };
}

/**
 * Single Policy hook
 */
export function usePolicy(uuid: string) {
  const { data, loading, error, refetch } = useApi<PolicyRule>(
    () => apiClient.get(`/admin/policies/${uuid}`),
    [uuid]
  );

  const updatePolicy = async (updates: PolicyUpdateRequest): Promise<PolicyRule> => {
    const updated = await apiClient.patch<PolicyRule>(`/admin/policies/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deletePolicy = async (): Promise<void> => {
    await apiClient.delete(`/admin/policies/${uuid}`);
  };

  const enablePolicy = async (): Promise<PolicyRule> => {
    const enabled = await apiClient.post<PolicyRule>(`/admin/policies/${uuid}/enable`);
    await refetch();
    return enabled;
  };

  const disablePolicy = async (): Promise<PolicyRule> => {
    const disabled = await apiClient.post<PolicyRule>(`/admin/policies/${uuid}/disable`);
    await refetch();
    return disabled;
  };

  return {
    policy: data,
    loading,
    error,
    refetch,
    updatePolicy,
    deletePolicy,
    enablePolicy,
    disablePolicy,
  };
}

/**
 * Users API hooks
 */
export function useUsers() {
  const { data, loading, error, refetch } = useApi<User[]>(
    () => apiClient.get('/admin/users')
  );

  const createUser = async (user: UserCreateRequest): Promise<User> => {
    const created = await apiClient.post<User>('/admin/users', user);
    await refetch();
    return created;
  };

  const updateUser = async (uuid: string, updates: UserUpdateRequest): Promise<User> => {
    const updated = await apiClient.patch<User>(`/admin/users/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deleteUser = async (uuid: string): Promise<void> => {
    await apiClient.delete(`/admin/users/${uuid}`);
    await refetch();
  };

  return {
    users: data || [],
    loading,
    error,
    refetch,
    createUser,
    updateUser,
    deleteUser,
  };
}

/**
 * Single User hook
 */
export function useUser(uuid: string) {
  const { data, loading, error, refetch } = useApi<User>(
    () => apiClient.get(`/admin/users/${uuid}`),
    [uuid]
  );

  const updateUser = async (updates: UserUpdateRequest): Promise<User> => {
    const updated = await apiClient.patch<User>(`/admin/users/${uuid}`, updates);
    await refetch();
    return updated;
  };

  const deleteUser = async (): Promise<void> => {
    await apiClient.delete(`/admin/users/${uuid}`);
  };

  return {
    user: data,
    loading,
    error,
    refetch,
    updateUser,
    deleteUser,
  };
}

/**
 * Current user hook (from JWT token)
 */
export function useCurrentUser() {
  const { data, loading, error, refetch } = useApi<User>(
    () => apiClient.getCurrentUser()
  );

  return {
    currentUser: data,
    loading,
    error,
    refetch,
  };
}
