'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  Activity,
  Shield,
  Filter,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import Link from 'next/link';

export default function RequestsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [appFilter, setAppFilter] = useState('');
  const [modelFilter, setModelFilter] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Get request stats - auto refresh every 5 seconds
  const { data: stats } = useQuery({
    queryKey: ['request-stats'],
    queryFn: () => api.getRequestStats(),
    refetchInterval: 5000,
  });

  // Get filter values (unique apps, models, statuses)
  const { data: filterValues } = useQuery({
    queryKey: ['request-filter-values'],
    queryFn: () => api.getRequestFilterValues(),
    staleTime: 60000, // Cache for 1 minute
  });

  // Get request logs with filters - auto refresh every 5 seconds
  const { data: logsData, isLoading } = useQuery({
    queryKey: ['request-logs', page, pageSize, appFilter, modelFilter, decisionFilter, statusFilter],
    queryFn: () => api.getRequestLogs({
      page,
      page_size: pageSize,
      app_id: appFilter || undefined,
      model: modelFilter || undefined,
      decision: decisionFilter || undefined,
      status: statusFilter || undefined,
    }),
    refetchInterval: 5000,
  });

  const logs = logsData?.items || [];
  const totalPages = logsData?.total_pages || 1;

  // Get unique values for filters from backend
  const uniqueApps = filterValues?.apps || [];
  const uniqueModels = filterValues?.models || [];

  const handleResetFilters = () => {
    setAppFilter('');
    setModelFilter('');
    setDecisionFilter('');
    setStatusFilter('');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Request Logs</h1>
        <p className="text-gray-500 mt-1">
          View recent gateway requests for debugging and observability
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Requests</p>
              <p className="text-2xl font-bold">{stats?.total_requests ?? '-'}</p>
            </div>
            <Activity className="w-8 h-8 text-blue-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Allowed</p>
              <p className="text-2xl font-bold text-green-600">{stats?.allowed_requests ?? '-'}</p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Warned</p>
              <p className="text-2xl font-bold text-yellow-600">{stats?.warned_requests ?? '-'}</p>
            </div>
            <AlertTriangle className="w-8 h-8 text-yellow-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Blocked</p>
              <p className="text-2xl font-bold text-red-600">{stats?.blocked_requests ?? '-'}</p>
            </div>
            <XCircle className="w-8 h-8 text-red-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Block Rate</p>
              <p className="text-2xl font-bold">{stats?.block_rate ?? 0}%</p>
            </div>
            <Shield className="w-8 h-8 text-gray-500" />
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Requests</h2>
          <div className="text-sm text-gray-500">
            {logsData?.total ?? 0} total
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Filters</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <select
              value={appFilter}
              onChange={(e) => { setAppFilter(e.target.value); setPage(1); }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Apps</option>
              {uniqueApps.map((app) => (
                <option key={app} value={app!}>{app}</option>
              ))}
            </select>

            <select
              value={modelFilter}
              onChange={(e) => { setModelFilter(e.target.value); setPage(1); }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Models</option>
              {uniqueModels.map((model) => (
                <option key={model} value={model!}>{model}</option>
              ))}
            </select>

            <select
              value={decisionFilter}
              onChange={(e) => { setDecisionFilter(e.target.value); setPage(1); }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Decisions</option>
              <option value="allow">Allowed</option>
              <option value="warn">Warned</option>
              <option value="block">Blocked</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Status</option>
              <option value="success">Success</option>
              <option value="pending">Pending</option>
              <option value="error">Error</option>
            </select>

            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={10}>10 per page</option>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>

            <button
              onClick={handleResetFilters}
              className="px-3 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm rounded-lg transition-colors"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Request ID</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">App</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Model</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Decision</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Status</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Tokens</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Time</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-500">
                    <Activity className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p className="text-lg font-medium">No requests found</p>
                    <p className="text-sm mt-1">
                      Make API calls to see request logs here
                    </p>
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-3 px-4 text-sm font-mono">
                      <Link
                        href={`/requests/${log.request_id}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {log.request_id?.slice(0, 12) ?? 'N/A'}...
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-900">{log.app_id ?? '-'}</td>
                    <td className="py-3 px-4 text-sm text-gray-600">{log.model ?? '-'}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                          log.decision === 'allow' ? 'bg-green-100 text-green-700' :
                          log.decision === 'warn' ? 'bg-yellow-100 text-yellow-700' :
                          log.decision === 'block' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {log.decision === 'allow' && <><CheckCircle className="w-3 h-3" />Allowed</>}
                        {log.decision === 'warn' && <><AlertTriangle className="w-3 h-3" />Warned</>}
                        {log.decision === 'block' && <><XCircle className="w-3 h-3" />Blocked</>}
                        {!log.decision && <>-</>}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                          log.status === 'success' ? 'bg-blue-100 text-blue-700' :
                          log.status === 'pending' ? 'bg-gray-100 text-gray-700' :
                          (log.status === 'error' || log.status === 'blocked') ? 'bg-orange-100 text-orange-700' :
                          'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {log.status === 'success' && <>Success</>}
                        {log.status === 'pending' && <>Pending</>}
                        {(log.status === 'error' || log.status === 'blocked') && <>Error</>}
                        {!log.status && <>-</>}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {log.input_tokens || log.output_tokens ? (
                        <span>{log.input_tokens ?? 0} / {log.output_tokens ?? 0}</span>
                      ) : '-'}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Page {page} of {totalPages} ({logsData?.total ?? 0} total)
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center gap-1"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors flex items-center gap-1"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
