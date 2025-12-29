'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Budget, Application } from '@/lib/api';
import {
  Wallet,
  Plus,
  Trash2,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Edit2,
  X,
  Save,
} from 'lucide-react';

export default function BudgetsPage() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingBudget, setEditingBudget] = useState<string | null>(null);
  const [editLimit, setEditLimit] = useState<number>(0);

  // Form state for create
  const [newAppId, setNewAppId] = useState('');
  const [newLimit, setNewLimit] = useState<number>(100);

  // Fetch budgets
  const { data: budgetsData, isLoading } = useQuery({
    queryKey: ['budgets'],
    queryFn: () => api.getBudgets(),
    refetchInterval: 10000,
  });

  // Fetch applications for dropdown
  const { data: applications } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.getApplications(),
  });

  // Create budget mutation
  const createMutation = useMutation({
    mutationFn: (data: { app_id: string; limit_usd: number }) => api.createBudget(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      setShowCreateModal(false);
      setNewAppId('');
      setNewLimit(100);
    },
  });

  // Update budget mutation
  const updateMutation = useMutation({
    mutationFn: ({ uuid, limit_usd }: { uuid: string; limit_usd: number }) =>
      api.updateBudget(uuid, { limit_usd }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      setEditingBudget(null);
    },
  });

  // Delete budget mutation
  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => api.deleteBudget(uuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });

  // Reset budget mutation
  const resetMutation = useMutation({
    mutationFn: (uuid: string) => api.resetBudget(uuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });

  const budgets = budgetsData?.items || [];

  // Apps that don't have a budget yet
  const availableApps = applications?.filter(
    (app) => !budgets.some((b) => b.app_id === app.app_id)
  ) || [];

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAppId || newLimit <= 0) return;
    createMutation.mutate({ app_id: newAppId, limit_usd: newLimit });
  };

  const handleStartEdit = (budget: Budget) => {
    setEditingBudget(budget.uuid);
    setEditLimit(budget.limit_usd);
  };

  const handleSaveEdit = (uuid: string) => {
    if (editLimit <= 0) return;
    updateMutation.mutate({ uuid, limit_usd: editLimit });
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Safety Budgets</h1>
          <p className="text-gray-500 mt-1">
            Set spending limits per application to prevent runaway costs
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          disabled={availableApps.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="w-4 h-4" />
          Add Budget
        </button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Budgets</p>
              <p className="text-2xl font-bold">{budgets.length}</p>
            </div>
            <Wallet className="w-8 h-8 text-blue-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Under Limit</p>
              <p className="text-2xl font-bold text-green-600">
                {budgets.filter((b) => !b.is_exceeded).length}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Exceeded</p>
              <p className="text-2xl font-bold text-red-600">
                {budgets.filter((b) => b.is_exceeded).length}
              </p>
            </div>
            <AlertTriangle className="w-8 h-8 text-red-500" />
          </div>
        </div>
      </div>

      {/* Budget List */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Application Budgets</h2>

        {isLoading ? (
          <div className="py-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          </div>
        ) : budgets.length === 0 ? (
          <div className="py-12 text-center text-gray-500">
            <Wallet className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-lg font-medium">No budgets configured</p>
            <p className="text-sm mt-1">
              Create a budget to limit spending per application
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {budgets.map((budget) => (
              <div
                key={budget.uuid}
                className={`border rounded-lg p-4 ${
                  budget.is_exceeded ? 'border-red-200 bg-red-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg ${
                        budget.is_exceeded ? 'bg-red-100' : 'bg-blue-100'
                      }`}
                    >
                      <Wallet
                        className={`w-5 h-5 ${
                          budget.is_exceeded ? 'text-red-600' : 'text-blue-600'
                        }`}
                      />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {budget.app_name || budget.app_id}
                      </h3>
                      <p className="text-sm text-gray-500">{budget.app_id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {budget.is_exceeded && (
                      <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        Exceeded
                      </span>
                    )}
                    <button
                      onClick={() => resetMutation.mutate(budget.uuid)}
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Reset spent amount"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleStartEdit(budget)}
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Edit limit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Delete this budget?')) {
                          deleteMutation.mutate(budget.uuid);
                        }
                      }}
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete budget"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mb-2">
                  <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        budget.usage_percent >= 100
                          ? 'bg-red-500'
                          : budget.usage_percent >= 80
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(100, budget.usage_percent)}%` }}
                    />
                  </div>
                </div>

                {/* Amount details */}
                <div className="flex items-center justify-between text-sm">
                  <div>
                    <span className="text-gray-600">Spent: </span>
                    <span className="font-medium">{formatCurrency(budget.spent_usd)}</span>
                  </div>
                  {editingBudget === budget.uuid ? (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-600">Limit: $</span>
                      <input
                        type="number"
                        value={editLimit}
                        onChange={(e) => setEditLimit(Number(e.target.value))}
                        className="w-24 px-2 py-1 border rounded text-right"
                        min="1"
                        step="1"
                      />
                      <button
                        onClick={() => handleSaveEdit(budget.uuid)}
                        className="p-1 text-green-600 hover:bg-green-50 rounded"
                      >
                        <Save className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setEditingBudget(null)}
                        className="p-1 text-gray-500 hover:bg-gray-100 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div>
                      <span className="text-gray-600">Limit: </span>
                      <span className="font-medium">{formatCurrency(budget.limit_usd)}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-gray-600">Remaining: </span>
                    <span
                      className={`font-medium ${
                        budget.remaining_usd <= 0 ? 'text-red-600' : 'text-green-600'
                      }`}
                    >
                      {formatCurrency(Math.max(0, budget.remaining_usd))}
                    </span>
                  </div>
                  <div>
                    <span
                      className={`font-bold ${
                        budget.usage_percent >= 100
                          ? 'text-red-600'
                          : budget.usage_percent >= 80
                          ? 'text-yellow-600'
                          : 'text-gray-600'
                      }`}
                    >
                      {budget.usage_percent.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Create Budget</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Application
                </label>
                <select
                  value={newAppId}
                  onChange={(e) => setNewAppId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select an application</option>
                  {availableApps.map((app) => (
                    <option key={app.uuid} value={app.app_id}>
                      {app.name} ({app.app_id})
                    </option>
                  ))}
                </select>
                {availableApps.length === 0 && (
                  <p className="text-sm text-yellow-600 mt-1">
                    All applications already have a budget
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Monthly Limit (USD)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                    $
                  </span>
                  <input
                    type="number"
                    value={newLimit}
                    onChange={(e) => setNewLimit(Number(e.target.value))}
                    className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="1"
                    step="1"
                    required
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Requests will be blocked when this limit is exceeded
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newAppId || newLimit <= 0 || createMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Budget'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
