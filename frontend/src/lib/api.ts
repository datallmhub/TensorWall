// Production: Direct API calls to backend
// Development: Use /api proxy (Next.js rewrites to localhost:8000)
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export interface Application {
  uuid: string;
  app_id: string;
  name: string;
  owner: string;
  description?: string;
  is_active: boolean;
  allowed_providers: string[];
  allowed_models: string[];
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  app_id: string;
  name: string;
  owner: string;
  description?: string;
  allowed_providers?: string[];
  allowed_models?: string[];
}

export interface ApplicationUpdate {
  name?: string;
  owner?: string;
  description?: string;
  is_active?: boolean;
  allowed_providers?: string[];
  allowed_models?: string[];
}

export interface ModelDetail {
  id: number;
  model_id: string;
  name: string;
  description?: string;
  provider: string;
  provider_model_id: string;
  base_url?: string;
  has_api_key: boolean;  // True if API key is configured (never expose the actual key)
  context_length: number;
  supports_vision: boolean;
  supports_functions: boolean;
  supports_streaming: boolean;
  input_cost_per_million: number;
  output_cost_per_million: number;
  is_enabled: boolean;
  is_default: boolean;
  display_order: number;
}

export interface ModelCreate {
  model_id: string;
  name: string;
  description?: string;
  provider: string;
  provider_model_id: string;
  base_url?: string;
  api_key_env_var?: string;
  api_key?: string;  // Direct API key for cloud providers (OSS)
  context_length?: number;
  supports_vision?: boolean;
  supports_functions?: boolean;
  supports_streaming?: boolean;
  input_cost_per_million?: number;
  output_cost_per_million?: number;
  is_enabled?: boolean;
  is_default?: boolean;
  display_order?: number;
}

export interface Policy {
  uuid: string;
  name: string;
  description?: string;
  app_id: string;
  user_email?: string;
  rule_type: string;
  conditions: Record<string, any>;
  action: string;
  priority: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginatedPolicies {
  items: Policy[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PolicyFilters {
  page?: number;
  page_size?: number;
  app_id?: string;
  user_email?: string;
  action?: string;
  is_enabled?: boolean;
}

// Request Logs (OSS)
export interface RequestLogItem {
  id: number;
  request_id: string | null;
  timestamp: string;
  app_id: string | null;
  feature: string | null;
  environment: string | null;
  model: string | null;
  provider: string | null;
  decision: string | null;
  status: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  error: string | null;
}

export interface RequestLogList {
  items: RequestLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RequestDetail {
  id: number;
  request_id: string | null;
  timestamp: string;
  app_id: string | null;
  feature: string | null;
  environment: string | null;
  model: string | null;
  provider: string | null;
  decision: string | null;
  blocked: boolean;
  policy_reason: string | null;
  security_issues: string[] | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  error: string | null;
}

export interface RequestStats {
  period_hours?: number;
  total_requests: number;
  blocked_requests: number;
  warned_requests: number;
  allowed_requests: number;
  block_rate: number;
  unique_apps: number;
  unique_models: number;
}

export interface RequestLogFilters {
  page?: number;
  page_size?: number;
  app_id?: string;
  model?: string;
  decision?: string;
  status?: string;
}

// Users (OSS - Admin Access Only)
export interface UserItem {
  id: number;
  uuid: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface UserList {
  items: UserItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserCreate {
  email: string;
  name: string;
  password?: string;
}

export interface UserUpdate {
  name?: string;
  is_active?: boolean;
}

export interface TraceDetail {
  decision: {
    status: string;
    blocked: boolean;
    risk_categories: string[];
    policies_evaluated: string[];
    estimated_cost_avoided: number;
  };
  context: {
    request_id: string;
    trace_id: string | null;
    user_email: string;
    app_id: string;
    feature: string;
    environment: string;
    tenant_id: string | null;
    session_id: string | null;
  };
  metrics: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost_usd: number;
    cost_breakdown: {
      input_cost_usd: number;
      output_cost_usd: number;
      input_price_per_1m: number;
      output_price_per_1m: number;
      pricing_version: string;
      pricing_source: string;
    } | null;
    latency_ms: number;
    provider: string | null;
    model: string | null;
  };
  timeline: {
    timestamp_start: string | null;
    timestamp_end: string | null;
    duration_ms: number | null;
    breakdown: {
      policy_evaluation_ms: number;
      budget_check_ms: number;
      provider_call_ms: number;
      total_overhead_ms: number;
    } | null;
  };
  explainability: {
    decision_reasons: string[];
    budget_snapshot: any;
  };
  content: {
    storage_enabled: boolean;
    prompt: string | null;
    response: string | null;
    message: string | null;
  };
  metadata: {
    status: string | null;
    error_message: string | null;
    extra_metadata: any;
  };
}

export interface SystemSettings {
  store_prompts: boolean;
  audit_retention_days: number;
  default_max_tokens: number;
  default_max_context: number;
  max_latency_ms: number;
}

export interface ApiKey {
  id: number;
  key_prefix: string;
  name: string;
  environment: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  api_key: string;
}

export interface Feature {
  name: string;
  description: string | null;
  enabled: boolean;
  allowed_actions: string[];
  allowed_models: string[];
  denied_models: string[];
  max_input_tokens: number | null;
  max_output_tokens: number | null;
  allowed_environments: string[];
  denied_environments: string[];
  require_json_output: boolean;
  rate_limit_per_minute: number | null;
  rate_limit_per_hour: number | null;
  max_cost_per_request_usd: number | null;
}

// Budget (OSS - Safety Budget)
export interface Budget {
  uuid: string;
  app_id: string;
  app_name: string | null;
  limit_usd: number;
  spent_usd: number;
  remaining_usd: number;
  usage_percent: number;
  period: string;
  is_exceeded: boolean;
}

export interface BudgetList {
  items: Budget[];
  total: number;
}

export interface BudgetCreate {
  app_id: string;
  limit_usd: number;
  period?: string;
}

export interface BudgetUpdate {
  limit_usd: number;
}

class ApiClient {
  /**
   * Get JWT token from localStorage
   */
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('jwt_token');
  }

  /**
   * Clear JWT token from localStorage
   */
  private clearToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt_token');
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    // Add Authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized - Token expired or invalid
    if (response.status === 401) {
      this.clearToken();
      if (typeof window !== 'undefined') {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
      }
      throw new Error('Unauthorized - Please login again');
    }

    // Handle 403 Forbidden
    if (response.status === 403) {
      const error = await response.json().catch(() => ({ detail: 'Permission denied' }));
      throw new Error(error.detail || 'Permission denied');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle 204 No Content (e.g., DELETE responses)
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Health
  async getHealth() {
    return this.request<{ status: string; timestamp: string; version: string }>('/health');
  }

  // Applications
  async getApplications() {
    return this.request<Application[]>('/admin/applications');
  }

  async getApplication(appUuid: string) {
    return this.request<Application>(`/admin/applications/${appUuid}`);
  }

  async createApplication(data: ApplicationCreate) {
    return this.request<Application>('/admin/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateApplication(appUuid: string, data: ApplicationUpdate) {
    return this.request<Application>(`/admin/applications/${appUuid}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteApplication(appUuid: string) {
    return this.request<void>(`/admin/applications/${appUuid}`, {
      method: 'DELETE',
    });
  }

  // Policies
  async getPolicies(filters?: PolicyFilters) {
    let url = '/admin/policies';
    const params = new URLSearchParams();

    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());
    if (filters?.app_id) params.append('app_id', filters.app_id);
    if (filters?.user_email) params.append('user_email', filters.user_email);
    if (filters?.action) params.append('action', filters.action);
    if (filters?.is_enabled !== undefined) params.append('is_enabled', filters.is_enabled.toString());

    if (params.toString()) url += `?${params}`;
    return this.request<PaginatedPolicies>(url);
  }

  async createPolicy(data: Partial<Policy>) {
    return this.request<Policy>('/admin/policies', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deletePolicy(uuid: string) {
    return this.request<void>(`/admin/policies/${uuid}`, {
      method: 'DELETE',
    });
  }

  async updatePolicy(uuid: string, data: Partial<{
    name: string;
    app_id: string;
    user_email: string;
    rule_type: string;
    conditions: Record<string, unknown>;
    action: string;
    priority: number;
    is_enabled: boolean;
  }>) {
    return this.request<Policy>(`/admin/policies/${uuid}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Chat (for playground)
  async chat(
    model: string,
    messages: { role: string; content: string }[],
    options?: {
      llmApiKey?: string;
      gatewayApiKey?: string;
      temperature?: number;
      maxTokens?: number;
    }
  ) {
    const headers: Record<string, string> = {};
    if (options?.llmApiKey) {
      headers['Authorization'] = `Bearer ${options.llmApiKey}`;
    }
    if (options?.gatewayApiKey) {
      headers['X-API-Key'] = options.gatewayApiKey;
    }

    return this.request<{
      id: string;
      object: string;
      created: number;
      model: string;
      choices: Array<{
        index: number;
        message: { role: string; content: string };
        finish_reason: string;
      }>;
      usage?: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
      };
    }>('/v1/chat/completions', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model,
        messages,
        ...(options?.temperature !== undefined && { temperature: options.temperature }),
        ...(options?.maxTokens !== undefined && { max_tokens: options.maxTokens }),
      }),
    });
  }

  // Models
  async getModels() {
    return this.request<{
      models: Array<{
        id: string;
        name: string;
        provider: string;
        description?: string;
        available: boolean;
        context_length?: number;
        supports_vision?: boolean;
        supports_functions?: boolean;
      }>;
      providers: Array<{
        name: string;
        available: boolean;
        base_url?: string;
        model_count: number;
      }>;
    }>('/admin/models');
  }

  async discoverModels(provider: 'ollama' | 'lmstudio') {
    return this.request<{ message: string; created: number; skipped: number }>(
      `/admin/models/discover/${provider}`,
      { method: 'POST' }
    );
  }

  async getAllModels() {
    return this.request<ModelDetail[]>('/admin/models/all');
  }

  async createModel(data: ModelCreate) {
    return this.request<ModelDetail>('/admin/models', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateModel(modelId: string, data: Partial<ModelCreate>) {
    // Use /by-id/ prefix to support model IDs with slashes (e.g., "local/phi-4")
    return this.request<ModelDetail>(`/admin/models/by-id/${modelId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteModel(modelId: string) {
    // Use /by-id/ prefix to support model IDs with slashes
    return this.request<void>(`/admin/models/by-id/${modelId}`, {
      method: 'DELETE',
    });
  }

  async enableModel(modelId: string) {
    // Use /by-id/ prefix to support model IDs with slashes
    return this.request<ModelDetail>(`/admin/models/by-id/${modelId}/enable`, {
      method: 'POST',
    });
  }

  async disableModel(modelId: string) {
    // Use /by-id/ prefix to support model IDs with slashes
    return this.request<ModelDetail>(`/admin/models/by-id/${modelId}/disable`, {
      method: 'POST',
    });
  }

  async seedModels() {
    return this.request<{ message: string; created: number; skipped: number }>(
      '/admin/models/seed',
      { method: 'POST' }
    );
  }

  async getProviders() {
    return this.request<Array<{
      name: string;
      available: boolean;
      base_url?: string;
      model_count?: number;
    }>>('/admin/models/providers/status');
  }

  // Settings
  async getSystemSettings() {
    return this.request<SystemSettings>('/admin/settings');
  }

  async updateSystemSettings(data: Partial<SystemSettings>) {
    return this.request<SystemSettings>('/admin/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // API Keys
  async getApiKeys(appUuid: string) {
    return this.request<ApiKey[]>(`/admin/applications/${appUuid}/keys`);
  }

  async createApiKey(appUuid: string, data: { name: string; environment: string }) {
    return this.request<ApiKeyCreated>(`/admin/applications/${appUuid}/keys`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async revokeApiKey(appUuid: string, keyId: number) {
    return this.request<void>(`/admin/applications/${appUuid}/keys/${keyId}`, {
      method: 'DELETE',
    });
  }

  async rotateApiKey(appUuid: string, keyId: number) {
    return this.request<ApiKeyCreated>(`/admin/applications/${appUuid}/keys/${keyId}/rotate`, {
      method: 'POST',
    });
  }

  // Features
  async getFeatures(appId: string) {
    return this.request<Feature[]>(`/admin/features/${appId}`);
  }

  async createFeature(appId: string, data: Partial<Feature>) {
    return this.request<Feature>(`/admin/features/${appId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteFeature(appId: string, featureName: string) {
    return this.request<void>(`/admin/features/${appId}/${featureName}`, {
      method: 'DELETE',
    });
  }

  // Request Logs (OSS)
  async getRequestLogs(filters?: RequestLogFilters) {
    let url = '/admin/requests';
    const params = new URLSearchParams();

    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());
    if (filters?.app_id) params.append('app_id', filters.app_id);
    if (filters?.model) params.append('model', filters.model);
    if (filters?.decision) params.append('decision', filters.decision);
    if (filters?.status) params.append('status', filters.status);

    if (params.toString()) url += `?${params}`;
    return this.request<RequestLogList>(url);
  }

  async getRequestDetail(requestId: string) {
    return this.request<RequestDetail>(`/admin/requests/${requestId}`);
  }

  async getRequestStats() {
    return this.request<RequestStats>(`/admin/requests/stats/summary`);
  }

  async getRequestFilterValues() {
    return this.request<{ apps: string[]; models: string[]; decisions: string[]; statuses: string[] }>(
      `/admin/requests/filters/values`
    );
  }

  // Users (OSS - Admin Access Only)
  async getUsers(page: number = 1, pageSize: number = 25) {
    return this.request<UserList>(`/admin/users?page=${page}&page_size=${pageSize}`);
  }

  async getUser(userId: number) {
    return this.request<UserItem>(`/admin/users/${userId}`);
  }

  async createUser(data: UserCreate) {
    return this.request<UserItem>('/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(userId: number, data: UserUpdate) {
    return this.request<UserItem>(`/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(userId: number) {
    return this.request<void>(`/admin/users/${userId}`, {
      method: 'DELETE',
    });
  }

  async resetUserPassword(userId: number, newPassword: string) {
    return this.request<{ message: string }>(`/admin/users/${userId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword }),
    });
  }

  // Budgets (OSS - Safety Budget)
  async getBudgets(appId?: string) {
    let url = '/admin/budgets';
    if (appId) url += `?app_id=${appId}`;
    return this.request<BudgetList>(url);
  }

  async createBudget(data: BudgetCreate) {
    return this.request<Budget>('/admin/budgets', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateBudget(uuid: string, data: BudgetUpdate) {
    return this.request<Budget>(`/admin/budgets/${uuid}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteBudget(uuid: string) {
    return this.request<void>(`/admin/budgets/${uuid}`, {
      method: 'DELETE',
    });
  }

  async resetBudget(uuid: string) {
    return this.request<Budget>(`/admin/budgets/${uuid}/reset`, {
      method: 'POST',
    });
  }

  // Security (OSS - LLM Security Guard)
  async getSecurityReport(period: string = '7d') {
    return this.request<SecurityReport>(`/admin/security/report?period=${period}`);
  }

  async getSecurityPosture() {
    return this.request<SecurityPosture>('/admin/security/posture');
  }

  async getSecurityRules() {
    return this.request<SecurityRule[]>('/admin/security/rules');
  }

  async getSecurityThreats(period: string = '7d') {
    return this.request<ThreatMetrics>(`/admin/security/threats?period=${period}`);
  }
}

// Security Types
export interface SecurityRule {
  name: string;
  category: string;
  action: string;
  scope: string;
  mandatory: boolean;
  enabled: boolean;
  description: string;
  owasp_mapping: string | null;
}

export interface ThreatMetrics {
  total_blocked: number;
  by_category: Record<string, number>;
  trend_7d: Array<{ date: string; blocked: number }>;
}

export interface OWASPAlignment {
  id: string;
  name: string;
  status: string;
  coverage: string;
}

export interface SecurityPosture {
  status: string;
  message: string;
  active_rules: number;
  total_rules: number;
  owasp_coverage: OWASPAlignment[];
}

export interface SecurityReport {
  posture: SecurityPosture;
  threats: ThreatMetrics;
  rules: SecurityRule[];
}

export const api = new ApiClient();
