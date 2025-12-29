'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, SystemSettings } from '@/lib/api';
import {
  Settings as SettingsIcon,
  ExternalLink,
} from 'lucide-react';
import Link from 'next/link';

export default function SettingsPage() {
  const queryClient = useQueryClient();

  const { data: systemSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: () => api.getSystemSettings(),
  });

  const updateSettingsMutation = useMutation({
    mutationFn: (data: Partial<SystemSettings>) => api.updateSystemSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Manage system configuration</p>
      </div>

      {/* System Settings */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-blue-100 rounded-lg">
            <SettingsIcon className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold">System Configuration</h3>
            <p className="text-sm text-gray-500">
              These settings affect the entire gateway
            </p>
          </div>
        </div>

        {settingsLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          </div>
        ) : (
          <div className="space-y-4 max-w-2xl">
            {/* Store Prompts */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <label className="font-medium text-gray-900">Store Prompts & Responses</label>
                <p className="text-sm text-gray-500 mt-1">
                  Enable storage of prompts and responses for debugging (GDPR-sensitive)
                </p>
              </div>
              <button
                onClick={() =>
                  updateSettingsMutation.mutate({ store_prompts: !systemSettings?.store_prompts })
                }
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  systemSettings?.store_prompts ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    systemSettings?.store_prompts ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Audit Retention */}
            <div className="p-4 border rounded-lg">
              <label className="block font-medium text-gray-900 mb-1">Audit Retention Days</label>
              <p className="text-sm text-gray-500 mb-3">Number of days to retain audit logs</p>
              <input
                type="number"
                value={systemSettings?.audit_retention_days || 90}
                onChange={(e) =>
                  updateSettingsMutation.mutate({ audit_retention_days: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="1"
                max="730"
              />
            </div>

            {/* Default Max Tokens */}
            <div className="p-4 border rounded-lg">
              <label className="block font-medium text-gray-900 mb-1">Default Max Tokens</label>
              <p className="text-sm text-gray-500 mb-3">Default maximum tokens per request</p>
              <input
                type="number"
                value={systemSettings?.default_max_tokens || 4096}
                onChange={(e) =>
                  updateSettingsMutation.mutate({ default_max_tokens: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="1"
                max="128000"
              />
            </div>

            {/* Max Latency */}
            <div className="p-4 border rounded-lg">
              <label className="block font-medium text-gray-900 mb-1">Max Latency (ms)</label>
              <p className="text-sm text-gray-500 mb-3">Maximum allowed latency for gateway processing</p>
              <input
                type="number"
                value={systemSettings?.max_latency_ms || 50}
                onChange={(e) =>
                  updateSettingsMutation.mutate({ max_latency_ms: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="1"
                max="30000"
              />
            </div>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Links</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/applications"
            className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div>
              <p className="font-medium text-gray-900">Applications</p>
              <p className="text-sm text-gray-500">Manage apps and API keys</p>
            </div>
            <ExternalLink className="w-4 h-4 text-gray-400" />
          </Link>
          <Link
            href="/policies"
            className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div>
              <p className="font-medium text-gray-900">Guardrails</p>
              <p className="text-sm text-gray-500">Configure policies</p>
            </div>
            <ExternalLink className="w-4 h-4 text-gray-400" />
          </Link>
          <Link
            href="/budgets"
            className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div>
              <p className="font-medium text-gray-900">Spend Protection</p>
              <p className="text-sm text-gray-500">Manage budgets</p>
            </div>
            <ExternalLink className="w-4 h-4 text-gray-400" />
          </Link>
        </div>
      </div>
    </div>
  );
}
