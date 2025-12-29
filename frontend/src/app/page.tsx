'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Activity,
  Shield,
  TrendingUp,
  Layers,
  Settings,
  MessageSquare,
  Cpu
} from 'lucide-react';

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'blue',
  onClick
}: {
  title: string;
  value: string | number;
  icon: any;
  trend?: string;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple';
  onClick?: () => void;
}) {
  const colors = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    purple: 'bg-purple-500',
  };

  return (
    <div
      className={`bg-white rounded-xl shadow-sm p-6 ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {trend && (
            <p className="text-sm text-green-600 mt-1 flex items-center">
              <TrendingUp className="w-4 h-4 mr-1" />
              {trend}
            </p>
          )}
        </div>
        <div className={`${colors[color]} p-3 rounded-lg`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  );
}

function QuickLink({
  title,
  description,
  href,
  icon: Icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: any;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-4 p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="p-3 bg-gray-100 rounded-lg">
        <Icon className="w-6 h-6 text-gray-600" />
      </div>
      <div>
        <p className="font-medium text-gray-900">{title}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
    </Link>
  );
}

export default function Dashboard() {
  const router = useRouter();

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.getHealth(),
    refetchInterval: 30000,
  });

  const { data: applications } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.getApplications(),
  });

  const { data: policies } = useQuery({
    queryKey: ['policies'],
    queryFn: () => api.getPolicies({ page_size: 100 }),
  });

  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: () => api.getModels(),
  });

  const { data: requestStats } = useQuery({
    queryKey: ['requestStats'],
    queryFn: () => api.getRequestStats(),
    refetchInterval: 5000,
  });

  const activeApps = applications?.filter((a) => a.is_active !== false).length ?? 0;
  const totalPolicies = policies?.total ?? 0;
  const enabledModels = modelsData?.models?.filter((m) => m.available).length ?? 0;
  const totalProviders = modelsData?.providers?.filter((p) => p.available).length ?? 0;
  const totalRequests = requestStats?.total_requests ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm sm:text-base text-gray-500 mt-1">TensorWall</p>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600">
            {health?.status === 'healthy' ? 'System Healthy' : 'System Down'}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Applications"
          value={applications?.length ?? 0}
          icon={Layers}
          trend={`${activeApps} active`}
          color="blue"
          onClick={() => router.push('/applications')}
        />
        <StatCard
          title="Guardrails"
          value={totalPolicies}
          icon={Shield}
          trend="Policies configured"
          color="green"
          onClick={() => router.push('/policies')}
        />
        <StatCard
          title="Models"
          value={enabledModels}
          icon={Cpu}
          trend={`${totalProviders} providers`}
          color="yellow"
          onClick={() => router.push('/admin/models')}
        />
        <StatCard
          title="Requests"
          value={totalRequests}
          icon={Activity}
          trend="View history"
          color="purple"
          onClick={() => router.push('/requests')}
        />
      </div>

      {/* Quick Links */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <QuickLink
            title="Playground"
            description="Test your LLM configurations"
            href="/playground"
            icon={MessageSquare}
          />
          <QuickLink
            title="Applications"
            description="Manage apps and API keys"
            href="/applications"
            icon={Layers}
          />
          <QuickLink
            title="Guardrails"
            description="Configure policies"
            href="/policies"
            icon={Shield}
          />
          <QuickLink
            title="Models"
            description="Manage LLM models"
            href="/admin/models"
            icon={Cpu}
          />
          <QuickLink
            title="Requests"
            description="View request history"
            href="/requests"
            icon={Activity}
          />
          <QuickLink
            title="Settings"
            description="System configuration"
            href="/settings"
            icon={Settings}
          />
        </div>
      </div>

      {/* Getting Started */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Getting Started</h2>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold">
              1
            </div>
            <div>
              <p className="font-medium text-gray-900">Create an Application</p>
              <p className="text-sm text-gray-500">
                Applications group your API keys and configurations.{' '}
                <Link href="/applications" className="text-blue-600 hover:underline">
                  Create one now
                </Link>
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold">
              2
            </div>
            <div>
              <p className="font-medium text-gray-900">Generate an API Key</p>
              <p className="text-sm text-gray-500">
                Each application can have multiple API keys for different environments.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold">
              3
            </div>
            <div>
              <p className="font-medium text-gray-900">Configure Guardrails</p>
              <p className="text-sm text-gray-500">
                Set up policies to control model access and token limits.{' '}
                <Link href="/policies" className="text-blue-600 hover:underline">
                  Configure policies
                </Link>
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold">
              4
            </div>
            <div>
              <p className="font-medium text-gray-900">Test in Playground</p>
              <p className="text-sm text-gray-500">
                Use the playground to test your LLM configurations.{' '}
                <Link href="/playground" className="text-blue-600 hover:underline">
                  Open playground
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
