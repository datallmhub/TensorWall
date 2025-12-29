'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  Plus,
  Search,
  Edit2,
  Trash2,
  Check,
  X,
  Eye,
  EyeOff,
  RefreshCw,
  Download,
  Server,
  Zap,
  Image as ImageIcon,
  Code,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Key,
} from 'lucide-react';
import { api, ModelDetail, ModelCreate } from '@/lib/api';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'lmstudio', label: 'LM Studio' },
  { value: 'aws_bedrock', label: 'AWS Bedrock' },
  { value: 'groq', label: 'Groq' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'google', label: 'Google' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'xai', label: 'xAI' },
  { value: 'together', label: 'Together AI' },
  { value: 'azure_openai', label: 'Azure OpenAI' },
];

// Local providers that don't need API keys
const LOCAL_PROVIDERS = ['ollama', 'lmstudio'];

function ProviderBadge({ provider }: { provider: string }) {
  const colors: Record<string, string> = {
    openai: 'bg-green-100 text-green-800',
    anthropic: 'bg-orange-100 text-orange-800',
    ollama: 'bg-purple-100 text-purple-800',
    lmstudio: 'bg-blue-100 text-blue-800',
    aws_bedrock: 'bg-yellow-100 text-yellow-800',
    groq: 'bg-red-100 text-red-800',
    mistral: 'bg-indigo-100 text-indigo-800',
    google: 'bg-cyan-100 text-cyan-800',
    deepseek: 'bg-pink-100 text-pink-800',
    xai: 'bg-gray-100 text-gray-800',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[provider] || 'bg-gray-100 text-gray-800'}`}>
      {provider}
    </span>
  );
}

export default function ModelsPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [providerFilter, setProviderFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<ModelCreate>>({
    model_id: '',
    name: '',
    provider: 'openai',
    provider_model_id: '',
    context_length: 4096,
    is_enabled: true,
    supports_streaming: true,
  });

  // Fetch all models
  const { data: models = [], isLoading, error: fetchError } = useQuery({
    queryKey: ['models-all'],
    queryFn: () => api.getAllModels(),
  });

  // Fetch providers status
  const { data: providers = [] } = useQuery({
    queryKey: ['providers'],
    queryFn: () => api.getProviders(),
  });

  // Create model mutation
  const createMutation = useMutation({
    mutationFn: (data: ModelCreate) => api.createModel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models-all'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
      setIsCreateModalOpen(false);
      resetForm();
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // Update model mutation
  const updateMutation = useMutation({
    mutationFn: ({ modelId, data }: { modelId: string; data: Partial<ModelCreate> }) =>
      api.updateModel(modelId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models-all'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
      setIsEditModalOpen(false);
      setSelectedModel(null);
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // Delete model mutation
  const deleteMutation = useMutation({
    mutationFn: (modelId: string) => api.deleteModel(modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models-all'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
      setIsDeleteModalOpen(false);
      setSelectedModel(null);
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // Enable/Disable model mutation
  const toggleMutation = useMutation({
    mutationFn: ({ modelId, enable }: { modelId: string; enable: boolean }) =>
      enable ? api.enableModel(modelId) : api.disableModel(modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models-all'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // Discover models mutations
  const discoverOllamaMutation = useMutation({
    mutationFn: () => api.discoverModels('ollama'),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['models-all'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
      alert(data.message);
    },
    onError: (err: Error) => {
      alert(`Error: ${err.message}`);
    },
  });

  const discoverLmstudioMutation = useMutation({
    mutationFn: () => api.discoverModels('lmstudio'),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['models-all'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
      alert(data.message);
    },
    onError: (err: Error) => {
      alert(`Error: ${err.message}`);
    },
  });

  // Seed models mutation
  const seedMutation = useMutation({
    mutationFn: () => api.seedModels(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['models-all'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
      alert(data.message);
    },
    onError: (err: Error) => {
      alert(`Error: ${err.message}`);
    },
  });

  const resetForm = () => {
    setFormData({
      model_id: '',
      name: '',
      provider: 'openai',
      provider_model_id: '',
      context_length: 4096,
      is_enabled: true,
      supports_streaming: true,
    });
    setError(null);
  };

  const handleEdit = (model: ModelDetail) => {
    setSelectedModel(model);
    setFormData({
      name: model.name,
      description: model.description || '',
      base_url: model.base_url || '',
      context_length: model.context_length,
      supports_vision: model.supports_vision,
      supports_functions: model.supports_functions,
      supports_streaming: model.supports_streaming,
      input_cost_per_million: model.input_cost_per_million,
      output_cost_per_million: model.output_cost_per_million,
      display_order: model.display_order,
    });
    setIsEditModalOpen(true);
    setError(null);
  };

  const handleDelete = (model: ModelDetail) => {
    setSelectedModel(model);
    setIsDeleteModalOpen(true);
    setError(null);
  };

  const handleToggle = (model: ModelDetail) => {
    toggleMutation.mutate({ modelId: model.model_id, enable: !model.is_enabled });
  };

  // Filter models
  const filteredModels = models.filter((model) => {
    const matchesSearch =
      model.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      model.model_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      model.provider.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesProvider = !providerFilter || model.provider === providerFilter;
    return matchesSearch && matchesProvider;
  });

  // Pagination
  const totalPages = Math.ceil(filteredModels.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedModels = filteredModels.slice(startIndex, startIndex + pageSize);

  // Reset to page 1 when filters change
  const handleFilterChange = (newFilter: string) => {
    setProviderFilter(newFilter);
    setCurrentPage(1);
  };

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  // Group by provider for stats
  const providerStats = models.reduce((acc, model) => {
    acc[model.provider] = (acc[model.provider] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Models</h1>
          <p className="text-gray-500 mt-1">Manage LLM models available in the gateway</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="flex items-center px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <Download className="w-4 h-4 mr-2" />
            {seedMutation.isPending ? 'Seeding...' : 'Seed Defaults'}
          </button>
          <button
            onClick={() => {
              resetForm();
              setIsCreateModalOpen(true);
            }}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Model
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {(error || fetchError) && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-600" />
          <p className="text-red-700">{error || (fetchError as Error)?.message}</p>
          <button onClick={() => setError(null)} className="ml-auto text-red-600 hover:text-red-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Models</p>
              <p className="text-2xl font-bold mt-1">{models.length}</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-lg">
              <Cpu className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Enabled</p>
              <p className="text-2xl font-bold mt-1">{models.filter((m) => m.is_enabled).length}</p>
            </div>
            <div className="bg-green-100 p-3 rounded-lg">
              <Check className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Providers</p>
              <p className="text-2xl font-bold mt-1">{Object.keys(providerStats).length}</p>
            </div>
            <div className="bg-purple-100 p-3 rounded-lg">
              <Server className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Vision Models</p>
              <p className="text-2xl font-bold mt-1">{models.filter((m) => m.supports_vision).length}</p>
            </div>
            <div className="bg-orange-100 p-3 rounded-lg">
              <ImageIcon className="w-6 h-6 text-orange-600" aria-hidden="true" />
            </div>
          </div>
        </div>
      </div>

      {/* Provider Discovery */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Local Model Discovery</h2>
        <div className="flex flex-wrap gap-4">
          {providers.filter(p => ['ollama', 'lmstudio'].includes(p.name)).map((provider) => (
            <div
              key={provider.name}
              className={`flex items-center gap-3 p-4 border rounded-lg ${
                provider.available ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className={`w-3 h-3 rounded-full ${provider.available ? 'bg-green-500' : 'bg-gray-400'}`} />
              <div>
                <p className="font-medium capitalize">{provider.name}</p>
                <p className="text-xs text-gray-500">{provider.base_url || 'Not configured'}</p>
              </div>
              {provider.available && (
                <button
                  onClick={() =>
                    provider.name === 'ollama'
                      ? discoverOllamaMutation.mutate()
                      : discoverLmstudioMutation.mutate()
                  }
                  disabled={discoverOllamaMutation.isPending || discoverLmstudioMutation.isPending}
                  className="ml-2 px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {(provider.name === 'ollama' && discoverOllamaMutation.isPending) ||
                  (provider.name === 'lmstudio' && discoverLmstudioMutation.isPending)
                    ? 'Discovering...'
                    : 'Discover'}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search models..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <select
            value={providerFilter}
            onChange={(e) => handleFilterChange(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Providers</option>
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label} ({providerStats[p.value] || 0})
              </option>
            ))}
          </select>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="10">10 per page</option>
            <option value="20">20 per page</option>
            <option value="50">50 per page</option>
            <option value="100">100 per page</option>
          </select>
        </div>
      </div>

      {/* Models Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Model</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Provider</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Context</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Capabilities</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Cost ($/1M)</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading models...
                  </td>
                </tr>
              ) : paginatedModels.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    No models found
                  </td>
                </tr>
              ) : (
                paginatedModels.map((model) => (
                  <tr key={model.model_id} className={`border-t hover:bg-gray-50 ${!model.is_enabled ? 'opacity-50' : ''}`}>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-gray-900">{model.name}</p>
                        <p className="text-xs text-gray-500 font-mono">{model.model_id}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <ProviderBadge provider={model.provider} />
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {model.context_length.toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-1">
                        {model.supports_vision && (
                          <span title="Vision" className="p-1 bg-orange-100 rounded">
                            <ImageIcon className="w-3 h-3 text-orange-600" aria-hidden="true" />
                          </span>
                        )}
                        {model.supports_functions && (
                          <span title="Functions" className="p-1 bg-blue-100 rounded">
                            <Code className="w-3 h-3 text-blue-600" />
                          </span>
                        )}
                        {model.supports_streaming && (
                          <span title="Streaming" className="p-1 bg-green-100 rounded">
                            <Zap className="w-3 h-3 text-green-600" />
                          </span>
                        )}
                        {model.has_api_key && (
                          <span title="API Key Configured" className="p-1 bg-yellow-100 rounded">
                            <Key className="w-3 h-3 text-yellow-600" />
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm">
                      <div className="flex items-center gap-1 text-gray-600">
                        <span>${model.input_cost_per_million.toFixed(2)}</span>
                        <span className="text-gray-400">/</span>
                        <span>${model.output_cost_per_million.toFixed(2)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleToggle(model)}
                        disabled={toggleMutation.isPending}
                        title={model.is_enabled ? 'Click to disable this model' : 'Click to enable this model'}
                        className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                          model.is_enabled
                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {model.is_enabled ? (
                          <>
                            <Eye className="w-3 h-3" /> Enabled
                          </>
                        ) : (
                          <>
                            <EyeOff className="w-3 h-3" /> Disabled
                          </>
                        )}
                      </button>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(model)}
                          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Edit2 className="w-4 h-4 text-gray-500" />
                        </button>
                        <button
                          onClick={() => handleDelete(model)}
                          className="p-2 hover:bg-red-100 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t bg-gray-50 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Showing {startIndex + 1}-{Math.min(startIndex + pageSize, filteredModels.length)} of {filteredModels.length} models
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-2 border rounded-lg text-sm hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
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
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-2 text-sm rounded-lg ${
                        currentPage === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'border hover:bg-white'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-2 border rounded-lg text-sm hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-semibold">Add New Model</h2>
              <button onClick={() => { setIsCreateModalOpen(false); resetForm(); }} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            {error && (
              <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createMutation.mutate(formData as ModelCreate);
              }}
              className="p-6 space-y-4"
            >
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Model ID *</label>
                  <input
                    type="text"
                    value={formData.model_id || ''}
                    onChange={(e) => setFormData({ ...formData, model_id: e.target.value })}
                    placeholder="e.g., gpt-4o, claude-3-opus"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Display Name *</label>
                  <input
                    type="text"
                    value={formData.name || ''}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., GPT-4o"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Provider *</label>
                  <select
                    value={formData.provider || 'openai'}
                    onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    {PROVIDERS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Provider Model ID *</label>
                  <input
                    type="text"
                    value={formData.provider_model_id || ''}
                    onChange={(e) => setFormData({ ...formData, provider_model_id: e.target.value })}
                    placeholder="Model ID used by the provider"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of the model"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base URL (optional)</label>
                <input
                  type="text"
                  value={formData.base_url || ''}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  placeholder="https://api.example.com/v1"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* API Key field - only for cloud providers */}
              {!LOCAL_PROVIDERS.includes(formData.provider || '') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <span className="flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      API Key (optional)
                    </span>
                  </label>
                  <input
                    type="password"
                    value={formData.api_key || ''}
                    onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    placeholder="sk-... or your provider API key"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Direct API key for this model. Leave empty to use environment variable.
                  </p>
                </div>
              )}

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Context Length</label>
                  <input
                    type="number"
                    value={formData.context_length || 4096}
                    onChange={(e) => setFormData({ ...formData, context_length: parseInt(e.target.value) || 4096 })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Input Cost ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={formData.input_cost_per_million || 0}
                    onChange={(e) => setFormData({ ...formData, input_cost_per_million: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Output Cost ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={formData.output_cost_per_million || 0}
                    onChange={(e) => setFormData({ ...formData, output_cost_per_million: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_vision || false}
                    onChange={(e) => setFormData({ ...formData, supports_vision: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Supports Vision</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_functions || false}
                    onChange={(e) => setFormData({ ...formData, supports_functions: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Supports Functions</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_streaming !== false}
                    onChange={(e) => setFormData({ ...formData, supports_streaming: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Supports Streaming</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_enabled !== false}
                    onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Enabled</span>
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => { setIsCreateModalOpen(false); resetForm(); }}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {createMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {createMutation.isPending ? 'Creating...' : 'Create Model'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && selectedModel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6 border-b flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">Edit Model</h2>
                <p className="text-sm text-gray-500 font-mono">{selectedModel.model_id}</p>
              </div>
              <button onClick={() => { setIsEditModalOpen(false); setSelectedModel(null); }} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            {error && (
              <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                updateMutation.mutate({ modelId: selectedModel.model_id, data: formData });
              }}
              className="p-6 space-y-4"
            >
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                <input
                  type="text"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                <input
                  type="text"
                  value={formData.base_url || ''}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* API Key field - only for cloud providers */}
              {selectedModel && !LOCAL_PROVIDERS.includes(selectedModel.provider) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    <span className="flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      API Key
                      {selectedModel.has_api_key && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                          Configured
                        </span>
                      )}
                    </span>
                  </label>
                  <input
                    type="password"
                    value={formData.api_key || ''}
                    onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    placeholder={selectedModel.has_api_key ? '••••••••••••••••' : 'Enter API key'}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {selectedModel.has_api_key
                      ? 'Leave empty to keep current key, or enter a new key to replace it.'
                      : 'Direct API key for this model. Leave empty to use environment variable.'}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Context Length</label>
                  <input
                    type="number"
                    value={formData.context_length || 0}
                    onChange={(e) => setFormData({ ...formData, context_length: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Input Cost ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={formData.input_cost_per_million || 0}
                    onChange={(e) => setFormData({ ...formData, input_cost_per_million: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Output Cost ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={formData.output_cost_per_million || 0}
                    onChange={(e) => setFormData({ ...formData, output_cost_per_million: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_vision || false}
                    onChange={(e) => setFormData({ ...formData, supports_vision: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Supports Vision</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_functions || false}
                    onChange={(e) => setFormData({ ...formData, supports_functions: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Supports Functions</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.supports_streaming !== false}
                    onChange={(e) => setFormData({ ...formData, supports_streaming: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Supports Streaming</span>
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => { setIsEditModalOpen(false); setSelectedModel(null); }}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {updateMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && selectedModel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 m-4">
            <h2 className="text-xl font-semibold mb-2">Delete Model</h2>
            <p className="text-gray-600 mb-4">
              Are you sure you want to delete <strong>{selectedModel.name}</strong>?
            </p>
            <p className="text-sm text-gray-500 font-mono mb-6 p-2 bg-gray-50 rounded">
              {selectedModel.model_id}
            </p>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setIsDeleteModalOpen(false); setSelectedModel(null); setError(null); }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(selectedModel.model_id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
              >
                {deleteMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
