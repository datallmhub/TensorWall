'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Clock,
  Cpu,
  DollarSign,
  Zap,
  AlertTriangle,
  Shield,
  Info,
} from 'lucide-react';

export default function RequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = params.id as string;

  const { data: request, isLoading, error } = useQuery({
    queryKey: ['request-detail', requestId],
    queryFn: () => api.getRequestDetail(requestId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading request details...</p>
        </div>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <XCircle className="w-12 h-12 mx-auto mb-3 text-red-500" />
          <p className="text-lg font-medium text-gray-900">Request Not Found</p>
          <p className="text-sm text-gray-500 mt-1">The request ID {requestId} could not be found</p>
          <button
            onClick={() => router.back()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Requests
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Request Detail</h1>
            <p className="text-gray-500 font-mono text-sm mt-1">{request.request_id}</p>
          </div>
          <span
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${
              request.decision === 'block'
                ? 'bg-red-100 text-red-700'
                : request.decision === 'warn'
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-green-100 text-green-700'
            }`}
          >
            {request.decision === 'block' ? (
              <>
                <XCircle className="w-4 h-4" />
                Blocked
              </>
            ) : request.decision === 'warn' ? (
              <>
                <AlertTriangle className="w-4 h-4" />
                Warned
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4" />
                Allowed
              </>
            )}
          </span>
        </div>
      </div>

      {/* Decision Reason (if blocked or warned) */}
      {request.decision === 'block' && request.policy_reason && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-red-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900">Blocked by Policy</h3>
              <p className="text-sm text-red-700 mt-1">{request.policy_reason}</p>
            </div>
          </div>
        </div>
      )}
      {request.decision === 'warn' && request.policy_reason && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-yellow-900">Warning from Policy</h3>
              <p className="text-sm text-yellow-700 mt-1">{request.policy_reason}</p>
            </div>
          </div>
        </div>
      )}

      {/* Security Issues */}
      {request.security_issues && request.security_issues.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-yellow-900">Security Issues Detected</h3>
              <ul className="mt-2 space-y-1">
                {request.security_issues.map((issue, idx) => (
                  <li key={idx} className="text-sm text-yellow-700">
                    • {issue}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Main Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Context */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold">Context</h2>
          </div>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-gray-500">Application</dt>
              <dd className="text-sm font-medium text-gray-900">{request.app_id ?? '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Feature</dt>
              <dd className="text-sm font-medium text-gray-900">{request.feature ?? '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Environment</dt>
              <dd>
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  {request.environment ?? 'unknown'}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Timestamp</dt>
              <dd className="text-sm font-medium text-gray-900 flex items-center gap-1">
                <Clock className="w-4 h-4 text-gray-400" />
                {new Date(request.timestamp).toLocaleString()}
              </dd>
            </div>
          </dl>
        </div>

        {/* Request Details */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold">Request Details</h2>
          </div>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-gray-500">Provider</dt>
              <dd className="text-sm font-medium text-gray-900">{request.provider ?? '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Model</dt>
              <dd className="text-sm font-medium text-gray-900">{request.model ?? '-'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Decision</dt>
              <dd className="text-sm font-medium text-gray-900">{request.decision ?? '-'}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Metrics (if available) */}
      {(request.input_tokens || request.cost_usd || request.latency_ms) && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold">Metrics</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {request.input_tokens !== null && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Input Tokens</p>
                <p className="text-xl font-bold">{request.input_tokens.toLocaleString()}</p>
              </div>
            )}
            {request.output_tokens !== null && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Output Tokens</p>
                <p className="text-xl font-bold">{request.output_tokens.toLocaleString()}</p>
              </div>
            )}
            {request.cost_usd !== null && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Cost</p>
                <p className="text-xl font-bold text-green-600">${request.cost_usd.toFixed(6)}</p>
              </div>
            )}
            {request.latency_ms !== null && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Latency</p>
                <p className="text-xl font-bold">{request.latency_ms} ms</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error (if any) */}
      {request.error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900">Error</h3>
              <p className="text-sm text-red-700 mt-1 font-mono">{request.error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
