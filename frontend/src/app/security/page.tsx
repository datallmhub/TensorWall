'use client';

import { useQuery } from '@tanstack/react-query';
import { api, SecurityReport, OWASPAlignment } from '@/lib/api';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  TrendingUp,
  Info,
} from 'lucide-react';

// =============================================================================
// Posture Card
// =============================================================================

function PostureCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">Security Posture</p>
          <div className="flex items-center gap-2 mt-2">
            <ShieldCheck className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-xl font-bold text-gray-900">Detection Active</p>
              <p className="text-sm text-gray-500">Monitoring all LLM requests</p>
            </div>
          </div>
        </div>
        <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
          Protected
        </span>
      </div>
    </div>
  );
}

// =============================================================================
// Metrics Cards
// =============================================================================

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
}: {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ElementType;
  color: 'red' | 'green' | 'blue' | 'yellow';
}) {
  const colors = {
    red: 'bg-red-50 border-red-200',
    green: 'bg-green-50 border-green-200',
    blue: 'bg-blue-50 border-blue-200',
    yellow: 'bg-yellow-50 border-yellow-200',
  };

  const iconColors = {
    red: 'text-red-500',
    green: 'text-green-500',
    blue: 'text-blue-500',
    yellow: 'text-yellow-500',
  };

  const textColors = {
    red: 'text-red-700',
    green: 'text-green-700',
    blue: 'text-blue-700',
    yellow: 'text-yellow-700',
  };

  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className={`text-sm font-medium ${textColors[color]}`}>{title}</p>
          <p className={`text-2xl font-bold mt-1 ${textColors[color]}`}>{value}</p>
          {subtitle && <p className={`text-xs mt-1 opacity-75 ${textColors[color]}`}>{subtitle}</p>}
        </div>
        <Icon className={`w-8 h-8 ${iconColors[color]}`} />
      </div>
    </div>
  );
}

// =============================================================================
// Trend Chart
// =============================================================================

function TrendChart({ data }: { data: Array<{ date: string; blocked: number }> }) {
  const maxBlocked = Math.max(...data.map(d => d.blocked), 1);

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-blue-600" />
        Threats Detected (Last 7 Days)
      </h3>
      <div className="flex items-end gap-2 h-32">
        {data.map((day) => {
          const height = (day.blocked / maxBlocked) * 100;
          const date = new Date(day.date);
          const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });

          return (
            <div key={day.date} className="flex-1 flex flex-col items-center">
              <div className="w-full bg-gray-100 rounded-t relative" style={{ height: '100px' }}>
                <div
                  className="absolute bottom-0 w-full bg-amber-500 rounded-t transition-all"
                  style={{ height: `${height}%` }}
                  title={`${day.blocked} detected`}
                />
              </div>
              <span className="text-xs text-gray-500 mt-2">{dayName}</span>
              <span className="text-xs font-medium text-gray-700">{day.blocked}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// OWASP Coverage Table
// =============================================================================

function OWASPTable({ coverage }: { coverage: OWASPAlignment[] }) {
  const statusColors = {
    full: 'bg-green-100 text-green-700',
    partial: 'bg-yellow-100 text-yellow-700',
    na: 'bg-gray-100 text-gray-500',
  };

  const statusLabels = {
    full: 'Full',
    partial: 'Partial',
    na: 'N/A',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600" />
          OWASP LLM Top 10 Coverage
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left py-3 px-6 text-sm font-medium text-gray-500">ID</th>
              <th className="text-left py-3 px-6 text-sm font-medium text-gray-500">Vulnerability</th>
              <th className="text-left py-3 px-6 text-sm font-medium text-gray-500">Status</th>
              <th className="text-left py-3 px-6 text-sm font-medium text-gray-500">Coverage</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {coverage.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="py-3 px-6">
                  <span className="font-mono text-sm font-medium text-blue-600">{item.id}</span>
                </td>
                <td className="py-3 px-6 font-medium text-gray-900">{item.name}</td>
                <td className="py-3 px-6">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColors[item.status as keyof typeof statusColors] || statusColors.na}`}>
                    {statusLabels[item.status as keyof typeof statusLabels] || item.status}
                  </span>
                </td>
                <td className="py-3 px-6 text-sm text-gray-600 max-w-xs">{item.coverage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =============================================================================
// Main Page
// =============================================================================

export default function SecurityPage() {
  const { data: report, isLoading, error } = useQuery({
    queryKey: ['security-report'],
    queryFn: () => api.getSecurityReport('7d'),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-red-800">Failed to load security report</h3>
        <p className="text-red-600 mt-2">{(error as Error).message}</p>
      </div>
    );
  }

  if (!report) return null;

  const { posture, threats } = report;

  // Calculate category totals
  const categoryEntries = Object.entries(threats.by_category);
  const topCategory = categoryEntries.length > 0
    ? categoryEntries.sort((a, b) => b[1] - a[1])[0]
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Shield className="w-7 h-7 text-blue-600" />
          Security Guard
        </h1>
        <p className="text-sm sm:text-base text-gray-500 mt-1">
          LLM security monitoring and threat detection
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start">
        <Info className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
        <div>
          <h3 className="font-medium text-blue-800">How Security Guard Works</h3>
          <p className="text-sm text-blue-700 mt-1">
            Security Guard analyzes every request for prompt injection, secrets, and PII.
            Threats are detected, scored, and logged. Check the Requests page for detailed analysis per request.
          </p>
        </div>
      </div>

      {/* Posture Card */}
      <PostureCard />

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Threats Detected (7d)"
          value={threats.total_blocked}
          subtitle="Logged for review"
          icon={AlertTriangle}
          color="yellow"
        />
        <MetricCard
          title="Top Category"
          value={topCategory ? topCategory[0] : 'None'}
          subtitle={topCategory ? `${topCategory[1]} detected` : 'No threats'}
          icon={ShieldAlert}
          color="blue"
        />
        <MetricCard
          title="OWASP Coverage"
          value={`${posture.owasp_coverage.filter(o => o.status === 'full').length}/10`}
          subtitle="Full coverage"
          icon={Shield}
          color="green"
        />
      </div>

      {/* Trend Chart */}
      <TrendChart data={threats.trend_7d} />

      {/* Threats by Category */}
      {categoryEntries.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Threats by Category
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {categoryEntries.map(([category, count]) => (
              <div key={category} className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className="text-sm text-gray-600 mt-1">{category}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* OWASP Coverage */}
      <OWASPTable coverage={posture.owasp_coverage} />
    </div>
  );
}
