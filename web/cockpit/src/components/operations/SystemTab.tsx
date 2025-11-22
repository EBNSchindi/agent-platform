'use client';

import { useEffect, useState } from 'react';
import { Activity, Database, Mail, TrendingUp, Cpu, AlertCircle, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';

interface DatabaseStats {
  emails_total: number;
  events_total: number;
  tasks_total: number;
  decisions_total: number;
  questions_total: number;
  database_size_mb: number | null;
}

interface ProcessingStats {
  emails_today: number;
  emails_this_week: number;
  emails_this_month: number;
  avg_confidence: number | null;
}

interface LLMProviderStatus {
  ollama_available: boolean;
  openai_configured: boolean;
  primary_provider: string;
}

interface SystemStatus {
  status: 'healthy' | 'degraded' | 'error';
  timestamp: string;
  database: DatabaseStats;
  processing: ProcessingStats;
  llm_providers: LLMProviderStatus;
  uptime: string | null;
}

export function SystemTab() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchSystemStatus = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/system/status');

      if (!response.ok) {
        throw new Error(`Failed to fetch system status: ${response.statusText}`);
      }

      const data = await response.json();
      setSystemStatus(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch system status');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
  }, []);

  if (isLoading && !systemStatus) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        <span className="ml-3 text-gray-600">Loading system status...</span>
      </div>
    );
  }

  if (error && !systemStatus) {
    return (
      <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
        <AlertCircle className="w-5 h-5 text-red-500" />
        <div>
          <p className="font-medium text-red-900">Failed to load system status</p>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!systemStatus) {
    return null;
  }

  const statusConfig = {
    healthy: {
      color: 'green',
      icon: CheckCircle,
      label: 'Healthy',
      bgClass: 'bg-green-100',
      textClass: 'text-green-800',
      iconClass: 'text-green-600',
    },
    degraded: {
      color: 'yellow',
      icon: AlertCircle,
      label: 'Degraded',
      bgClass: 'bg-yellow-100',
      textClass: 'text-yellow-800',
      iconClass: 'text-yellow-600',
    },
    error: {
      color: 'red',
      icon: XCircle,
      label: 'Error',
      bgClass: 'bg-red-100',
      textClass: 'text-red-800',
      iconClass: 'text-red-600',
    },
  };

  const config = statusConfig[systemStatus.status];
  const StatusIcon = config.icon;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            System Status
          </h2>
          {lastUpdated && (
            <p className="text-sm text-gray-600 mt-1">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
        <button
          onClick={fetchSystemStatus}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Overall Status */}
      <div className={`rounded-lg p-6 ${config.bgClass}`}>
        <div className="flex items-center gap-3">
          <StatusIcon className={`w-8 h-8 ${config.iconClass}`} />
          <div>
            <h3 className={`text-xl font-bold ${config.textClass}`}>
              System {config.label}
            </h3>
            <p className={`text-sm ${config.textClass}`}>
              All systems operational
            </p>
          </div>
        </div>
      </div>

      {/* Database Statistics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-blue-600" />
          Database Statistics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard
            label="Total Emails"
            value={systemStatus.database.emails_total.toLocaleString()}
            icon={Mail}
            color="blue"
          />
          <StatCard
            label="Events Logged"
            value={systemStatus.database.events_total.toLocaleString()}
            icon={Activity}
            color="purple"
          />
          <StatCard
            label="Tasks Extracted"
            value={systemStatus.database.tasks_total.toLocaleString()}
            icon={CheckCircle}
            color="green"
          />
          <StatCard
            label="Decisions"
            value={systemStatus.database.decisions_total.toLocaleString()}
            icon={TrendingUp}
            color="orange"
          />
          <StatCard
            label="Questions"
            value={systemStatus.database.questions_total.toLocaleString()}
            icon={AlertCircle}
            color="pink"
          />
          {systemStatus.database.database_size_mb !== null && (
            <StatCard
              label="Database Size"
              value={`${systemStatus.database.database_size_mb.toFixed(1)} MB`}
              icon={Database}
              color="gray"
            />
          )}
        </div>
      </div>

      {/* Processing Statistics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-600" />
          Processing Statistics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Today"
            value={systemStatus.processing.emails_today.toLocaleString()}
            subtext="emails processed"
            color="blue"
          />
          <StatCard
            label="This Week"
            value={systemStatus.processing.emails_this_week.toLocaleString()}
            subtext="emails processed"
            color="indigo"
          />
          <StatCard
            label="This Month"
            value={systemStatus.processing.emails_this_month.toLocaleString()}
            subtext="emails processed"
            color="purple"
          />
          {systemStatus.processing.avg_confidence !== null && (
            <StatCard
              label="Avg Confidence"
              value={`${(systemStatus.processing.avg_confidence * 100).toFixed(0)}%`}
              subtext="classification confidence"
              color="green"
            />
          )}
        </div>
      </div>

      {/* LLM Provider Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-purple-600" />
          LLM Providers
        </h3>
        <div className="space-y-3">
          <ProviderStatus
            name="Ollama (Local)"
            available={systemStatus.llm_providers.ollama_available}
            isPrimary={systemStatus.llm_providers.primary_provider === 'ollama'}
          />
          <ProviderStatus
            name="OpenAI (Cloud)"
            available={systemStatus.llm_providers.openai_configured}
            isPrimary={systemStatus.llm_providers.primary_provider === 'openai'}
          />
        </div>
        <div className="mt-4 pt-4 border-t">
          <p className="text-sm text-gray-600">
            Primary Provider: <span className="font-semibold">{systemStatus.llm_providers.primary_provider}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  subtext?: string;
  icon?: React.ComponentType<{ className?: string }>;
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'pink' | 'gray' | 'indigo';
}

function StatCard({ label, value, subtext, icon: Icon, color = 'blue' }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    orange: 'bg-orange-50 text-orange-700',
    pink: 'bg-pink-50 text-pink-700',
    gray: 'bg-gray-50 text-gray-700',
    indigo: 'bg-indigo-50 text-indigo-700',
  };

  return (
    <div className={`rounded-lg p-4 ${colorClasses[color]}`}>
      {Icon && (
        <Icon className="w-5 h-5 mb-2 opacity-70" />
      )}
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {subtext && (
        <p className="text-xs opacity-70 mt-1">{subtext}</p>
      )}
    </div>
  );
}

interface ProviderStatusProps {
  name: string;
  available: boolean;
  isPrimary: boolean;
}

function ProviderStatus({ name, available, isPrimary }: ProviderStatusProps) {
  return (
    <div className="flex items-center justify-between p-3 border rounded-lg">
      <div className="flex items-center gap-3">
        {available ? (
          <CheckCircle className="w-5 h-5 text-green-600" />
        ) : (
          <XCircle className="w-5 h-5 text-red-600" />
        )}
        <div>
          <p className="font-medium text-gray-900">{name}</p>
          <p className="text-sm text-gray-600">
            {available ? 'Available' : 'Not configured'}
          </p>
        </div>
      </div>
      {isPrimary && (
        <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded">
          Primary
        </span>
      )}
    </div>
  );
}
