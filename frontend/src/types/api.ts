/**
 * TypeScript interfaces for LLM Gateway API responses
 *
 * Version: 2.0.0 (Security Update)
 * - Changed all `id: number` to `uuid: string`
 * - Added UUID-based identifiers for all resources
 * - Aligned with backend security refactoring
 */

/**
 * Budget resource
 */
export interface Budget {
  uuid: string; // Changed from id: number
  scope: 'global' | 'application' | 'user';
  scope_id?: string;
  soft_limit_usd: number;
  hard_limit_usd: number;
  current_spend_usd: number;
  period_start?: string;
  period_end?: string;
  auto_reset: boolean;
  reset_frequency?: 'daily' | 'weekly' | 'monthly' | 'yearly';
  is_active: boolean;
  created_at: string;
  updated_at: string;
  owner_id?: number;
}

/**
 * Application resource
 */
export interface Application {
  uuid: string; // Changed from id: number
  app_id: string; // Human-readable ID (e.g., "my-app")
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  owner_id?: number;
}

/**
 * API Key resource
 */
export interface ApiKey {
  id: number; // API keys still use numeric ID internally
  key_id: string;
  key_prefix: string;
  name?: string;
  application_id: number; // Foreign key to applications.id
  is_active: boolean;
  expires_at?: string;
  created_at: string;
  last_used_at?: string;
}

/**
 * Policy Rule resource
 */
export interface PolicyRule {
  uuid: string; // Changed from id: number
  name: string;
  description?: string;
  rule_type: 'rate_limit' | 'content_filter' | 'cost_limit' | 'model_restriction';
  conditions: Record<string, any>;
  action: 'allow' | 'block' | 'warn' | 'throttle';
  priority: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
  owner_id?: number;
}

/**
 * User resource
 */
export interface User {
  uuid: string; // Changed from id: number
  email: string;
  name?: string;
  role: 'super_admin' | 'admin' | 'user' | 'viewer';
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

/**
 * User App Role resource
 */
export interface UserAppRole {
  id: number;
  user_id: number;
  application_id: number;
  role: string;
  created_at: string;
}

/**
 * Analytics Usage response
 */
export interface UsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  successful_requests: number;
  failed_requests: number;
  average_latency_ms: number;
  period_start: string;
  period_end: string;
}

/**
 * Analytics Usage by Model
 */
export interface UsageByModel {
  model_name: string;
  request_count: number;
  total_tokens: number;
  total_cost_usd: number;
  average_latency_ms: number;
}

/**
 * Analytics Usage by Feature
 */
export interface UsageByFeature {
  feature_name: string;
  request_count: number;
  total_tokens: number;
  total_cost_usd: number;
}

/**
 * Analytics Daily Usage
 */
export interface DailyUsage {
  date: string;
  request_count: number;
  total_tokens: number;
  total_cost_usd: number;
  unique_users: number;
}

/**
 * Audit Log entry
 */
export interface AuditLog {
  id: number;
  request_id: string;
  timestamp: string;
  application_id?: number;
  user_id?: number;
  endpoint: string;
  method: string;
  status_code: number;
  model_name?: string;
  tokens_used?: number;
  cost_usd?: number;
  latency_ms?: number;
  error_message?: string;
  metadata?: Record<string, any>;
}

/**
 * Request Trace
 */
export interface RequestTrace {
  request_id: string;
  timestamp: string;
  application_id?: number;
  user_id?: number;
  model_name: string;
  endpoint: string;
  status: 'success' | 'error' | 'blocked';
  latency_ms: number;
  tokens_used?: number;
  cost_usd?: number;
  error_message?: string;
  request_body?: Record<string, any>;
  response_body?: Record<string, any>;
  policy_results?: Array<{
    policy_id: number;
    policy_name: string;
    action: string;
    matched: boolean;
  }>;
}

/**
 * Analytics Overview
 */
export interface AnalyticsOverview {
  total_requests_today: number;
  total_cost_today_usd: number;
  total_tokens_today: number;
  active_applications: number;
  active_users: number;
  average_latency_ms: number;
  success_rate_percent: number;
  top_models: Array<{
    model_name: string;
    request_count: number;
  }>;
  top_applications: Array<{
    app_id: string;
    request_count: number;
  }>;
}

/**
 * SLO (Service Level Objectives) metrics
 */
export interface SLOMetrics {
  availability_percent: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  error_rate_percent: number;
  target_availability_percent: number;
  target_latency_p95_ms: number;
  target_error_rate_percent: number;
  period_start: string;
  period_end: string;
}

/**
 * API Error response
 */
export interface ApiError {
  detail: string;
  code?: string;
  status_code?: number;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * Budget Create/Update request
 */
export interface BudgetCreateRequest {
  scope: 'global' | 'application' | 'user';
  scope_id?: string;
  soft_limit_usd: number;
  hard_limit_usd: number;
  auto_reset?: boolean;
  reset_frequency?: 'daily' | 'weekly' | 'monthly' | 'yearly';
}

export interface BudgetUpdateRequest {
  soft_limit_usd?: number;
  hard_limit_usd?: number;
  auto_reset?: boolean;
  reset_frequency?: 'daily' | 'weekly' | 'monthly' | 'yearly';
  is_active?: boolean;
}

/**
 * Application Create/Update request
 */
export interface ApplicationCreateRequest {
  app_id: string;
  name: string;
  description?: string;
}

export interface ApplicationUpdateRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
}

/**
 * Policy Create/Update request
 */
export interface PolicyCreateRequest {
  name: string;
  description?: string;
  rule_type: 'rate_limit' | 'content_filter' | 'cost_limit' | 'model_restriction';
  conditions: Record<string, any>;
  action: 'allow' | 'block' | 'warn' | 'throttle';
  priority?: number;
}

export interface PolicyUpdateRequest {
  name?: string;
  description?: string;
  conditions?: Record<string, any>;
  action?: 'allow' | 'block' | 'warn' | 'throttle';
  priority?: number;
  is_enabled?: boolean;
}

/**
 * User Create/Update request
 */
export interface UserCreateRequest {
  email: string;
  name?: string;
  password: string;
  role?: 'admin' | 'user' | 'viewer';
}

export interface UserUpdateRequest {
  email?: string;
  name?: string;
  password?: string;
  role?: 'super_admin' | 'admin' | 'user' | 'viewer';
  is_active?: boolean;
}

/**
 * Auth Login request/response
 */
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}
