'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Application, ApplicationCreate, ApplicationUpdate, ApiKey } from '@/lib/api';
import { Plus, Trash2, Key, Copy, Check, X, Edit2, RefreshCw, Eye, EyeOff } from 'lucide-react';

const AVAILABLE_PROVIDERS = ['openai', 'anthropic', 'ollama', 'lmstudio', 'bedrock'];

interface AppFormData {
  name: string;
  app_id: string;
  owner: string;
  description: string;
  allowed_providers: string[];
  allowed_models: string[];
  is_active: boolean;
}

const defaultFormData: AppFormData = {
  name: '',
  app_id: '',
  owner: '',
  description: '',
  allowed_providers: ['openai', 'anthropic'],
  allowed_models: [],
  is_active: true,
};

function AppFormModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isEdit = false,
  isLoading = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: AppFormData) => void;
  initialData?: AppFormData;
  isEdit?: boolean;
  isLoading?: boolean;
}) {
  const [formData, setFormData] = useState<AppFormData>(initialData || defaultFormData);
  const [modelsInput, setModelsInput] = useState(initialData?.allowed_models?.join(', ') || '');

  if (!isOpen) return null;

  const handleProviderToggle = (provider: string) => {
    setFormData(prev => ({
      ...prev,
      allowed_providers: prev.allowed_providers.includes(provider)
        ? prev.allowed_providers.filter(p => p !== provider)
        : [...prev.allowed_providers, provider],
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data = {
      ...formData,
      allowed_models: modelsInput.split(',').map(m => m.trim()).filter(Boolean),
    };
    onSubmit(data);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-4 sm:p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">{isEdit ? 'Edit Application' : 'Create Application'}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Application Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="My Application"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              App ID (unique identifier) *
            </label>
            <input
              type="text"
              value={formData.app_id}
              onChange={(e) => setFormData({ ...formData, app_id: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="my-app"
              required
              disabled={isEdit}
            />
            {isEdit && <p className="text-xs text-gray-500 mt-1">App ID cannot be changed</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Owner (team/user) *
            </label>
            <input
              type="text"
              value={formData.owner}
              onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="team-backend"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Brief description of the application"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Allowed Providers
            </label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_PROVIDERS.map((provider) => (
                <button
                  key={provider}
                  type="button"
                  onClick={() => handleProviderToggle(provider)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    formData.allowed_providers.includes(provider)
                      ? 'bg-blue-100 text-blue-700 border-2 border-blue-500'
                      : 'bg-gray-100 text-gray-600 border-2 border-transparent hover:bg-gray-200'
                  }`}
                >
                  {provider}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Allowed Models (comma-separated, empty = all)
            </label>
            <input
              type="text"
              value={modelsInput}
              onChange={(e) => setModelsInput(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="gpt-4o, gpt-4o-mini, claude-3-5-sonnet"
            />
            <p className="text-xs text-gray-500 mt-1">Leave empty to allow all models from selected providers</p>
          </div>

          {isEdit && (
            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="is_active" className="ml-2 text-sm text-gray-700">
                Active
              </label>
            </div>
          )}

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
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : isEdit ? 'Save Changes' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ApiKeysModal({
  isOpen,
  onClose,
  application,
}: {
  isOpen: boolean;
  onClose: () => void;
  application: Application;
}) {
  const queryClient = useQueryClient();
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyEnv, setNewKeyEnv] = useState('development');
  const [showNewKey, setShowNewKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ['apiKeys', application.uuid],
    queryFn: () => api.getApiKeys(application.uuid),
    enabled: isOpen,
  });

  const createKeyMutation = useMutation({
    mutationFn: (data: { name: string; environment: string }) =>
      api.createApiKey(application.uuid, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys', application.uuid] });
      setShowNewKey(data.api_key);
      setNewKeyName('');
    },
  });

  const revokeKeyMutation = useMutation({
    mutationFn: (keyId: number) => api.revokeApiKey(application.uuid, keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys', application.uuid] });
    },
  });

  const rotateKeyMutation = useMutation({
    mutationFn: (keyId: number) => api.rotateApiKey(application.uuid, keyId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys', application.uuid] });
      setShowNewKey(data.api_key);
    },
  });

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-4 sm:p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">API Keys</h2>
            <p className="text-sm text-gray-500">{application.name} ({application.app_id})</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* New Key Created Alert */}
        {showNewKey && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-800">New API Key Created!</p>
                <p className="text-xs text-green-600 mt-1">Copy this key now. It won&apos;t be shown again.</p>
              </div>
              <button onClick={() => setShowNewKey(null)} className="text-green-600 hover:text-green-800">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="mt-2 flex items-center space-x-2">
              <code className="flex-1 text-sm bg-green-100 px-3 py-2 rounded font-mono break-all">
                {showNewKey}
              </code>
              <button
                onClick={() => copyToClipboard(showNewKey, 'new')}
                className="p-2 text-green-600 hover:text-green-800"
              >
                {copiedKey === 'new' ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
              </button>
            </div>
          </div>
        )}

        {/* Create New Key */}
        <div className="mb-6 p-3 sm:p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Create New API Key</h3>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g., Production Key)"
              className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2">
              <select
                value={newKeyEnv}
                onChange={(e) => setNewKeyEnv(e.target.value)}
                className="flex-1 sm:flex-none px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="development">Development</option>
                <option value="staging">Staging</option>
                <option value="production">Production</option>
              </select>
              <button
                onClick={() => createKeyMutation.mutate({ name: newKeyName, environment: newKeyEnv })}
                disabled={!newKeyName || createKeyMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
              >
                {createKeyMutation.isPending ? '...' : 'Create'}
              </button>
            </div>
          </div>
        </div>

        {/* Existing Keys */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Existing API Keys</h3>
          {isLoading ? (
            <p className="text-gray-500 text-center py-4">Loading...</p>
          ) : !apiKeys?.length ? (
            <p className="text-gray-500 text-center py-4">No API keys yet</p>
          ) : (
            <div className="space-y-3">
              {apiKeys.map((key) => (
                <div key={key.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-gray-50 rounded-lg gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center flex-wrap gap-2">
                      <span className="font-medium truncate">{key.name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        key.environment === 'production' ? 'bg-red-100 text-red-700' :
                        key.environment === 'staging' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {key.environment}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        key.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}>
                        {key.is_active ? 'Active' : 'Revoked'}
                      </span>
                    </div>
                    <div className="flex items-center flex-wrap gap-x-2 gap-y-1 mt-1">
                      <code className="text-sm text-gray-600">{key.key_prefix}...</code>
                      <span className="text-xs text-gray-400">
                        Created {new Date(key.created_at).toLocaleDateString()}
                      </span>
                      {key.last_used_at && (
                        <span className="text-xs text-gray-400">
                          • Last used {new Date(key.last_used_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 self-end sm:self-center">
                    <button
                      onClick={() => {
                        if (confirm('Rotate this key? The old key will be revoked.')) {
                          rotateKeyMutation.mutate(key.id);
                        }
                      }}
                      disabled={!key.is_active}
                      className="p-2 text-blue-600 hover:text-blue-800 disabled:opacity-50"
                      title="Rotate Key"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Revoke this key? This cannot be undone.')) {
                          revokeKeyMutation.mutate(key.id);
                        }
                      }}
                      disabled={!key.is_active}
                      className="p-2 text-red-600 hover:text-red-800 disabled:opacity-50"
                      title="Revoke Key"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ApplicationsPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingApp, setEditingApp] = useState<Application | null>(null);
  const [keysApp, setKeysApp] = useState<Application | null>(null);
  const queryClient = useQueryClient();

  const { data: applications, isLoading, error } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.getApplications(),
  });

  const createMutation = useMutation({
    mutationFn: (data: ApplicationCreate) => api.createApplication(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      setIsCreateModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, data }: { uuid: string; data: ApplicationUpdate }) =>
      api.updateApplication(uuid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      setEditingApp(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (appUuid: string) => api.deleteApplication(appUuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
    },
  });

  const handleCreate = (data: AppFormData) => {
    createMutation.mutate({
      app_id: data.app_id,
      name: data.name,
      owner: data.owner,
      description: data.description || undefined,
      allowed_providers: data.allowed_providers,
      allowed_models: data.allowed_models.length ? data.allowed_models : undefined,
    });
  };

  const handleUpdate = (data: AppFormData) => {
    if (!editingApp) return;
    updateMutation.mutate({
      uuid: editingApp.uuid,
      data: {
        name: data.name,
        owner: data.owner,
        description: data.description || undefined,
        is_active: data.is_active,
        allowed_providers: data.allowed_providers,
        allowed_models: data.allowed_models.length ? data.allowed_models : undefined,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-lg">
        Error loading applications: {(error as Error).message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Applications</h1>
          <p className="text-sm sm:text-base text-gray-500 mt-1">Manage your registered applications and API keys</p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 w-full sm:w-auto"
        >
          <Plus className="w-5 h-5 mr-2" />
          New Application
        </button>
      </div>

      {/* Desktop: Table View */}
      <div className="hidden md:block bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px]">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Application</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Owner</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Providers</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Status</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {applications?.map((app) => (
                <tr key={app.uuid} className="border-t hover:bg-gray-50">
                  <td className="py-4 px-6">
                    <div className="font-medium text-gray-900">{app.name}</div>
                    <div className="flex items-center space-x-2 mt-1">
                      <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{app.app_id}</code>
                      {app.description && (
                        <span className="text-xs text-gray-500 truncate max-w-xs">{app.description}</span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 px-6 text-gray-600">{app.owner}</td>
                  <td className="py-4 px-6">
                    <div className="flex flex-wrap gap-1">
                      {app.allowed_providers?.slice(0, 3).map((provider) => (
                        <span
                          key={provider}
                          className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded"
                        >
                          {provider}
                        </span>
                      ))}
                      {app.allowed_providers?.length > 3 && (
                        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                          +{app.allowed_providers.length - 3}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      app.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {app.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setKeysApp(app)}
                        className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded"
                        title="Manage API Keys"
                      >
                        <Key className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => setEditingApp(app)}
                        className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
                        title="Edit Application"
                      >
                        <Edit2 className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Are you sure you want to delete this application?')) {
                            deleteMutation.mutate(app.uuid);
                          }
                        }}
                        className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded"
                        title="Delete Application"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!applications?.length && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-500">
                    No applications yet. Create your first application to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile: Card View */}
      <div className="md:hidden space-y-4">
        {applications?.map((app) => (
          <div key={app.uuid} className="bg-white rounded-xl shadow-sm p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-medium text-gray-900 truncate">{app.name}</h3>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    app.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {app.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <code className="text-xs bg-gray-100 px-2 py-0.5 rounded mt-1 inline-block">{app.app_id}</code>
              </div>
            </div>

            {app.description && (
              <p className="text-sm text-gray-500 mt-2 line-clamp-2">{app.description}</p>
            )}

            <div className="mt-3 flex items-center text-sm text-gray-600">
              <span className="font-medium">Owner:</span>
              <span className="ml-2">{app.owner}</span>
            </div>

            <div className="mt-2">
              <div className="flex flex-wrap gap-1">
                {app.allowed_providers?.map((provider) => (
                  <span
                    key={provider}
                    className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded"
                  >
                    {provider}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t flex items-center justify-end space-x-2">
              <button
                onClick={() => setKeysApp(app)}
                className="flex items-center px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg"
              >
                <Key className="w-4 h-4 mr-1" />
                Keys
              </button>
              <button
                onClick={() => setEditingApp(app)}
                className="flex items-center px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                <Edit2 className="w-4 h-4 mr-1" />
                Edit
              </button>
              <button
                onClick={() => {
                  if (confirm('Are you sure you want to delete this application?')) {
                    deleteMutation.mutate(app.uuid);
                  }
                }}
                className="flex items-center px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Delete
              </button>
            </div>
          </div>
        ))}
        {!applications?.length && (
          <div className="bg-white rounded-xl shadow-sm p-8 text-center text-gray-500">
            No applications yet. Create your first application to get started.
          </div>
        )}
      </div>

      {/* Create Modal */}
      <AppFormModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreate}
        isLoading={createMutation.isPending}
      />

      {/* Edit Modal */}
      {editingApp && (
        <AppFormModal
          isOpen={true}
          onClose={() => setEditingApp(null)}
          onSubmit={handleUpdate}
          initialData={{
            name: editingApp.name,
            app_id: editingApp.app_id,
            owner: editingApp.owner,
            description: editingApp.description || '',
            allowed_providers: editingApp.allowed_providers || [],
            allowed_models: editingApp.allowed_models || [],
            is_active: editingApp.is_active,
          }}
          isEdit={true}
          isLoading={updateMutation.isPending}
        />
      )}

      {/* API Keys Modal */}
      {keysApp && (
        <ApiKeysModal
          isOpen={true}
          onClose={() => setKeysApp(null)}
          application={keysApp}
        />
      )}
    </div>
  );
}
