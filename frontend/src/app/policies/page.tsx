'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Policy, PolicyFilters } from '@/lib/api';
import { Plus, Trash2, Pencil, X, Shield, AlertTriangle, Search, ChevronLeft, ChevronRight } from 'lucide-react';

function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  policyName,
  isDeleting,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  policyName: string;
  isDeleting: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Delete Guardrail</h2>
        </div>

        <p className="text-gray-600 mb-6">
          Are you sure you want to delete <span className="font-medium text-gray-900">&quot;{policyName}&quot;</span>? This action cannot be undone.
        </p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

function CreatePolicyModal({
  isOpen,
  onClose,
  createMutation,
}: {
  isOpen: boolean;
  onClose: () => void;
  createMutation: any;
}) {
  const [formData, setFormData] = useState({
    name: '',
    app_id: '',
    rule_type: 'model_restriction',
    action: 'deny',
    priority: 100,
    // Condition fields
    models: '',
    environments: '',
    features: '',
    max_tokens: '',
    allowed_hours_start: '',
    allowed_hours_end: '',
  });

  // Fetch applications list
  const { data: applications = [] } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.getApplications(),
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-4 sm:p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Create Guardrail</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {createMutation.isError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">
              Failed to create guardrail: {(createMutation.error as any)?.message || 'Unknown error'}
            </p>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            // Build conditions based on rule_type
            const conditions: Record<string, any> = {};

            if (formData.rule_type === 'model_restriction' && formData.models) {
              conditions.models = formData.models.split(',').map(m => m.trim()).filter(Boolean);
            }
            if (formData.rule_type === 'environment_restriction' && formData.environments) {
              conditions.environments = formData.environments.split(',').map(e => e.trim()).filter(Boolean);
            }
            if (formData.rule_type === 'feature_restriction' && formData.features) {
              conditions.features = formData.features.split(',').map(f => f.trim()).filter(Boolean);
            }
            if (formData.rule_type === 'token_limit' && formData.max_tokens) {
              conditions.max_tokens = parseInt(formData.max_tokens);
            }
            if (formData.rule_type === 'time_restriction' && formData.allowed_hours_start && formData.allowed_hours_end) {
              conditions.allowed_hours = [parseInt(formData.allowed_hours_start), parseInt(formData.allowed_hours_end)];
            }

            const policyData = {
              name: formData.name,
              app_id: formData.app_id,
              rule_type: formData.rule_type,
              conditions,
              action: formData.action,
              priority: formData.priority,
            };
            console.log('Submitting policy:', policyData);
            createMutation.mutate(policyData);
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Policy Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Block GPT-4 in production"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Application <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.app_id}
              onChange={(e) => setFormData({ ...formData, app_id: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select an application</option>
              {applications.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.name} ({app.app_id})
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              The application to which this guardrail will apply
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Rule Type
            </label>
            <select
              value={formData.rule_type}
              onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="model_restriction">Model Restriction</option>
              <option value="environment_restriction">Environment Restriction</option>
              <option value="feature_restriction">Feature Restriction</option>
              <option value="token_limit">Token Limit</option>
              <option value="time_restriction">Time Restriction</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Type of restriction to apply
            </p>
          </div>

          {/* Dynamic condition fields based on rule_type */}
          {formData.rule_type === 'model_restriction' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Models
              </label>
              <input
                type="text"
                value={formData.models}
                onChange={(e) => setFormData({ ...formData, models: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="gpt-4o, claude-3-5-sonnet"
              />
              <p className="text-xs text-gray-500 mt-1">
                Comma-separated list of models to restrict
              </p>
            </div>
          )}

          {formData.rule_type === 'environment_restriction' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Environments
              </label>
              <input
                type="text"
                value={formData.environments}
                onChange={(e) => setFormData({ ...formData, environments: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="production, staging"
              />
              <p className="text-xs text-gray-500 mt-1">
                Comma-separated list of environments
              </p>
            </div>
          )}

          {formData.rule_type === 'feature_restriction' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Features
              </label>
              <input
                type="text"
                value={formData.features}
                onChange={(e) => setFormData({ ...formData, features: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="chat, summarize, translate"
              />
              <p className="text-xs text-gray-500 mt-1">
                Comma-separated list of features
              </p>
            </div>
          )}

          {formData.rule_type === 'token_limit' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Tokens
              </label>
              <input
                type="number"
                value={formData.max_tokens}
                onChange={(e) => setFormData({ ...formData, max_tokens: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="4000"
                min={1}
              />
              <p className="text-xs text-gray-500 mt-1">
                Maximum number of tokens allowed per request
              </p>
            </div>
          )}

          {formData.rule_type === 'time_restriction' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start Hour (0-23)
                </label>
                <input
                  type="number"
                  value={formData.allowed_hours_start}
                  onChange={(e) => setFormData({ ...formData, allowed_hours_start: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="9"
                  min={0}
                  max={23}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  End Hour (0-23)
                </label>
                <input
                  type="number"
                  value={formData.allowed_hours_end}
                  onChange={(e) => setFormData({ ...formData, allowed_hours_end: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="18"
                  min={0}
                  max={23}
                />
              </div>
              <p className="text-xs text-gray-500 col-span-2">
                Allowed time window (e.g., 9-18 for business hours)
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Action
            </label>
            <select
              value={formData.action}
              onChange={(e) => setFormData({ ...formData, action: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="allow">Allow</option>
              <option value="warn">Warn</option>
              <option value="deny">Deny</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority (higher = evaluated first)
            </label>
            <input
              type="number"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              min={1}
              max={1000}
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.app_id || !formData.name || createMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditPolicyModal({
  isOpen,
  onClose,
  policy,
  updateMutation,
}: {
  isOpen: boolean;
  onClose: () => void;
  policy: Policy | null;
  updateMutation: any;
}) {
  const [formData, setFormData] = useState({
    name: '',
    rule_type: 'model_restriction',
    action: 'deny',
    priority: 100,
    is_enabled: true,
    // Condition fields
    models: '',
    environments: '',
    features: '',
    max_tokens: '',
    allowed_hours_start: '',
    allowed_hours_end: '',
  });

  // Map rule_type to display label
  const ruleTypeLabels: Record<string, string> = {
    'model_restriction': 'Model',
    'environment_restriction': 'Environment',
    'feature_restriction': 'Feature',
    'token_limit': 'Token Limit',
    'time_restriction': 'Time',
    'general': 'General',
  };

  // Update form when policy changes
  useEffect(() => {
    if (policy) {
      const conditions = policy.conditions || {};
      setFormData({
        name: policy.name || '',
        rule_type: policy.rule_type || 'model_restriction',
        action: policy.action || 'deny',
        priority: policy.priority || 100,
        is_enabled: policy.is_enabled ?? true,
        models: conditions.models?.join(', ') || '',
        environments: conditions.environments?.join(', ') || '',
        features: conditions.features?.join(', ') || '',
        max_tokens: conditions.max_tokens?.toString() || '',
        allowed_hours_start: conditions.allowed_hours?.[0]?.toString() || '',
        allowed_hours_end: conditions.allowed_hours?.[1]?.toString() || '',
      });
    }
  }, [policy]);

  if (!isOpen || !policy) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Build conditions based on rule_type
    const conditions: Record<string, any> = {};
    if (formData.rule_type === 'model_restriction' && formData.models) {
      conditions.models = formData.models.split(',').map(m => m.trim()).filter(Boolean);
    }
    if (formData.rule_type === 'environment_restriction' && formData.environments) {
      conditions.environments = formData.environments.split(',').map(e => e.trim()).filter(Boolean);
    }
    if (formData.rule_type === 'feature_restriction' && formData.features) {
      conditions.features = formData.features.split(',').map(f => f.trim()).filter(Boolean);
    }
    if (formData.rule_type === 'token_limit' && formData.max_tokens) {
      conditions.max_tokens = parseInt(formData.max_tokens);
    }
    if (formData.rule_type === 'time_restriction' && formData.allowed_hours_start && formData.allowed_hours_end) {
      conditions.allowed_hours = [parseInt(formData.allowed_hours_start), parseInt(formData.allowed_hours_end)];
    }

    updateMutation.mutate({
      uuid: policy.uuid,
      data: {
        name: formData.name,
        rule_type: formData.rule_type,
        conditions,
        action: formData.action,
        priority: formData.priority,
        is_enabled: formData.is_enabled,
      },
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Edit Guardrail</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Read-only info */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Application:</span>{' '}
            <code className="bg-gray-200 px-1 rounded">{policy.app_id || '*'}</code>
          </p>
        </div>

        {updateMutation.isError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">
              Failed to update: {(updateMutation.error as any)?.message || 'Unknown error'}
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rule Type</label>
            <select
              value={formData.rule_type}
              onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="model_restriction">Model Restriction</option>
              <option value="environment_restriction">Environment Restriction</option>
              <option value="feature_restriction">Feature Restriction</option>
              <option value="token_limit">Token Limit</option>
              <option value="time_restriction">Time Restriction</option>
            </select>
          </div>

          {/* Dynamic condition fields based on rule_type */}
          {formData.rule_type === 'model_restriction' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Models</label>
              <input
                type="text"
                value={formData.models}
                onChange={(e) => setFormData({ ...formData, models: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="gpt-4o, claude-3-5-sonnet"
              />
              <p className="text-xs text-gray-500 mt-1">Comma-separated list of models</p>
            </div>
          )}

          {formData.rule_type === 'environment_restriction' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Environments</label>
              <input
                type="text"
                value={formData.environments}
                onChange={(e) => setFormData({ ...formData, environments: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="production, staging"
              />
              <p className="text-xs text-gray-500 mt-1">Comma-separated list of environments</p>
            </div>
          )}

          {formData.rule_type === 'feature_restriction' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Features</label>
              <input
                type="text"
                value={formData.features}
                onChange={(e) => setFormData({ ...formData, features: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="chat, summarize, translate"
              />
              <p className="text-xs text-gray-500 mt-1">Comma-separated list of features</p>
            </div>
          )}

          {formData.rule_type === 'token_limit' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
              <input
                type="number"
                value={formData.max_tokens}
                onChange={(e) => setFormData({ ...formData, max_tokens: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="4000"
                min={1}
              />
            </div>
          )}

          {formData.rule_type === 'time_restriction' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Start Hour (0-23)</label>
                <input
                  type="number"
                  value={formData.allowed_hours_start}
                  onChange={(e) => setFormData({ ...formData, allowed_hours_start: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  min={0}
                  max={23}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">End Hour (0-23)</label>
                <input
                  type="number"
                  value={formData.allowed_hours_end}
                  onChange={(e) => setFormData({ ...formData, allowed_hours_end: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  min={0}
                  max={23}
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
            <select
              value={formData.action}
              onChange={(e) => setFormData({ ...formData, action: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="allow">Allow</option>
              <option value="warn">Warn</option>
              <option value="deny">Deny</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
            <input
              type="number"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              min={1}
              max={1000}
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_enabled"
              checked={formData.is_enabled}
              onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
            />
            <label htmlFor="is_enabled" className="text-sm font-medium text-gray-700">
              Enabled
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function PoliciesPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editModal, setEditModal] = useState<{ isOpen: boolean; policy: Policy | null }>({
    isOpen: false,
    policy: null,
  });
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; policy: Policy | null }>({
    isOpen: false,
    policy: null,
  });
  const [filters, setFilters] = useState<PolicyFilters>({
    page: 1,
    page_size: 10,
  });
  const queryClient = useQueryClient();

  const { data: paginatedData, isLoading } = useQuery({
    queryKey: ['policies', filters],
    queryFn: () => api.getPolicies(filters),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => {
      console.log('Mutation function called with:', data);
      return api.createPolicy(data);
    },
    onSuccess: (data) => {
      console.log('✓ Policy created successfully:', data);
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      setIsModalOpen(false);
    },
    onError: (error: any) => {
      console.error('✗ Failed to create policy:', error);
      alert(`Failed to create guardrail: ${error.message || 'Unknown error'}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => api.deletePolicy(uuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      setDeleteModal({ isOpen: false, policy: null });
    },
    onError: (error: any) => {
      alert(`Failed to delete guardrail: ${error.message || 'Unknown error'}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, data }: { uuid: string; data: any }) => api.updatePolicy(uuid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      setEditModal({ isOpen: false, policy: null });
    },
    onError: (error: any) => {
      alert(`Failed to update guardrail: ${error.message || 'Unknown error'}`);
    },
  });

  const openEditModal = (policy: Policy) => {
    setEditModal({ isOpen: true, policy });
  };

  const openDeleteModal = (policy: Policy) => {
    setDeleteModal({ isOpen: true, policy });
  };

  const handleConfirmDelete = () => {
    if (deleteModal.policy) {
      deleteMutation.mutate(deleteModal.policy.uuid);
    }
  };

  const policies = paginatedData?.items || [];
  const totalPages = paginatedData?.total_pages || 1;
  const currentPage = paginatedData?.page || 1;
  const totalItems = paginatedData?.total || 0;

  // Fetch applications for filter dropdown
  const { data: applications = [] } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.getApplications(),
  });

  const actionColors: Record<string, string> = {
    allow: 'bg-green-100 text-green-700',
    warn: 'bg-yellow-100 text-yellow-700',
    deny: 'bg-red-100 text-red-700',
  };

  // Map rule_type to display label
  const ruleTypeLabels: Record<string, string> = {
    'model_restriction': 'Model',
    'environment_restriction': 'Environment',
    'feature_restriction': 'Feature',
    'token_limit': 'Token Limit',
    'time_restriction': 'Time',
    'general': 'General',
  };

  const ruleTypeColors: Record<string, string> = {
    'model_restriction': 'bg-purple-100 text-purple-700',
    'environment_restriction': 'bg-blue-100 text-blue-700',
    'feature_restriction': 'bg-indigo-100 text-indigo-700',
    'token_limit': 'bg-orange-100 text-orange-700',
    'time_restriction': 'bg-cyan-100 text-cyan-700',
    'general': 'bg-gray-100 text-gray-700',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Guardrails</h1>
          <p className="text-sm sm:text-base text-gray-500 mt-1">Protect your LLM usage with access control rules</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 w-full sm:w-auto"
        >
          <Plus className="w-5 h-5 mr-2" />
          New Guardrail
        </button>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start">
        <Shield className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
        <div>
          <h3 className="font-medium text-blue-800">How Guardrails Work</h3>
          <p className="text-sm text-blue-700 mt-1">
            Guardrails are evaluated in priority order (highest first). The first matching rule determines the action.
            Use <code className="bg-blue-100 px-1 rounded">*</code> for global rules that apply to all apps.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          <div className="grid grid-cols-2 sm:flex gap-2 sm:gap-4">
            <select
              value={filters.app_id || ''}
              onChange={(e) => setFilters({ ...filters, app_id: e.target.value || undefined, page: 1 })}
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Apps</option>
              {applications.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.name}
                </option>
              ))}
            </select>

            <select
              value={filters.action || ''}
              onChange={(e) => setFilters({ ...filters, action: e.target.value || undefined, page: 1 })}
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Actions</option>
              <option value="allow">Allow</option>
              <option value="warn">Warn</option>
              <option value="deny">Deny</option>
            </select>

            <select
              value={filters.is_enabled === undefined ? '' : filters.is_enabled.toString()}
              onChange={(e) => setFilters({ ...filters, is_enabled: e.target.value === '' ? undefined : e.target.value === 'true', page: 1 })}
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Status</option>
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </div>

          <div className="flex items-center justify-between sm:ml-auto gap-4">
            {(filters.app_id || filters.action || filters.is_enabled !== undefined) && (
              <button
                onClick={() => setFilters({ page: 1, page_size: 10 })}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Clear
              </button>
            )}
            <span className="text-sm text-gray-600">
              {totalItems} {totalItems === 1 ? 'policy' : 'policies'}
            </span>
          </div>
        </div>
      </div>

      {/* Desktop: Policies Table */}
      <div className="hidden md:block bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px]">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Name</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">App ID</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Type</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Conditions</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Action</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Priority</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Status</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((policy) => (
                <tr key={policy.uuid} className="border-t hover:bg-gray-50">
                  <td className="py-4 px-6">
                    <div className="font-medium text-gray-900">{policy.name?.split('\n')[0] || policy.name}</div>
                  </td>
                  <td className="py-4 px-6">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {policy.app_id || '*'}
                    </code>
                  </td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${ruleTypeColors[policy.rule_type] || 'bg-gray-100 text-gray-700'}`}>
                      {ruleTypeLabels[policy.rule_type] || policy.rule_type}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="text-sm text-gray-600">
                      {policy.conditions?.models && (
                        <span className="block">{policy.conditions.models.join(', ')}</span>
                      )}
                      {policy.conditions?.environments && (
                        <span className="block">{policy.conditions.environments.join(', ')}</span>
                      )}
                      {policy.conditions?.features && (
                        <span className="block">{policy.conditions.features.join(', ')}</span>
                      )}
                      {policy.conditions?.max_tokens && (
                        <span className="block">Max: {policy.conditions.max_tokens} tokens</span>
                      )}
                      {policy.conditions?.allowed_hours && (
                        <span className="block">{policy.conditions.allowed_hours[0]}h - {policy.conditions.allowed_hours[1]}h</span>
                      )}
                      {!policy.conditions?.models && !policy.conditions?.environments && !policy.conditions?.features && !policy.conditions?.max_tokens && !policy.conditions?.allowed_hours && (
                        <span className="text-gray-400">-</span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${actionColors[policy.action]}`}>
                      {policy.action}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-gray-600">{policy.priority}</td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      policy.is_enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {policy.is_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openEditModal(policy)}
                        disabled={updateMutation.isPending}
                        className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                        title="Edit"
                      >
                        <Pencil className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => openDeleteModal(policy)}
                        disabled={deleteMutation.isPending}
                        className="text-red-600 hover:text-red-800 disabled:opacity-50"
                        title="Delete"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile: Policies Card View */}
      <div className="md:hidden space-y-4">
        {policies.map((policy) => (
          <div key={policy.uuid} className="bg-white rounded-xl shadow-sm p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-medium text-gray-900 truncate">{policy.name}</h3>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${actionColors[policy.action]}`}>
                    {policy.action}
                  </span>
                </div>
                <code className="text-xs bg-gray-100 px-2 py-0.5 rounded mt-1 inline-block">
                  {policy.app_id || '*'}
                </code>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => openEditModal(policy)}
                  disabled={updateMutation.isPending}
                  className="text-blue-600 hover:text-blue-800 p-2 disabled:opacity-50"
                >
                  <Pencil className="w-5 h-5" />
                </button>
                <button
                  onClick={() => openDeleteModal(policy)}
                  disabled={deleteMutation.isPending}
                  className="text-red-600 hover:text-red-800 p-2 disabled:opacity-50"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${ruleTypeColors[policy.rule_type] || 'bg-gray-100 text-gray-700'}`}>
                {ruleTypeLabels[policy.rule_type] || policy.rule_type}
              </span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                policy.is_enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
              }`}>
                {policy.is_enabled ? 'Enabled' : 'Disabled'}
              </span>
              <span className="text-gray-500">Priority: {policy.priority}</span>
            </div>

            {/* Show conditions on mobile */}
            {(policy.conditions?.models || policy.conditions?.environments || policy.conditions?.features || policy.conditions?.max_tokens || policy.conditions?.allowed_hours) && (
              <div className="mt-2 text-xs text-gray-600">
                {policy.conditions?.models && <span className="block">Models: {policy.conditions.models.join(', ')}</span>}
                {policy.conditions?.environments && <span className="block">Envs: {policy.conditions.environments.join(', ')}</span>}
                {policy.conditions?.features && <span className="block">Features: {policy.conditions.features.join(', ')}</span>}
                {policy.conditions?.max_tokens && <span className="block">Max: {policy.conditions.max_tokens} tokens</span>}
                {policy.conditions?.allowed_hours && <span className="block">Hours: {policy.conditions.allowed_hours[0]}h - {policy.conditions.allowed_hours[1]}h</span>}
              </div>
            )}
          </div>
        ))}
        {policies.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-500">
            No policies found. Create your first guardrail.
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Page size - hidden on mobile */}
          <div className="hidden sm:flex items-center gap-2">
            <span className="text-sm text-gray-600">Show:</span>
            <select
              value={filters.page_size}
              onChange={(e) => setFilters({ ...filters, page_size: parseInt(e.target.value), page: 1 })}
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </div>

          {/* Pagination */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilters({ ...filters, page: currentPage - 1 })}
              disabled={currentPage === 1}
              className="flex items-center px-3 py-2 border rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="hidden sm:inline ml-1">Previous</span>
            </button>

            <div className="hidden sm:flex items-center gap-1">
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }

                return (
                  <button
                    key={pageNum}
                    onClick={() => setFilters({ ...filters, page: pageNum })}
                    className={`px-3 py-2 rounded-lg text-sm ${
                      currentPage === pageNum
                        ? 'bg-blue-600 text-white'
                        : 'border hover:bg-gray-50'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            {/* Mobile: Page indicator */}
            <span className="sm:hidden text-sm text-gray-600 px-2">
              {currentPage} / {totalPages}
            </span>

            <button
              onClick={() => setFilters({ ...filters, page: currentPage + 1 })}
              disabled={currentPage === totalPages}
              className="flex items-center px-3 py-2 border rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="hidden sm:inline mr-1">Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Page info - hidden on mobile */}
          <div className="hidden sm:block text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </div>
        </div>
      </div>

      <CreatePolicyModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        createMutation={createMutation}
      />

      <DeleteConfirmModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ isOpen: false, policy: null })}
        onConfirm={handleConfirmDelete}
        policyName={deleteModal.policy?.name?.split('\n')[0] || deleteModal.policy?.name || ''}
        isDeleting={deleteMutation.isPending}
      />

      <EditPolicyModal
        isOpen={editModal.isOpen}
        onClose={() => setEditModal({ isOpen: false, policy: null })}
        policy={editModal.policy}
        updateMutation={updateMutation}
      />
    </div>
  );
}
