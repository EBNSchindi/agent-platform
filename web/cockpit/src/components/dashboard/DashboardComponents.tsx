'use client';

import Link from 'next/link';
import {
  Mail, CheckCircle, AlertCircle, HelpCircle, Clock,
  Activity, Settings, User, Flag, GitBranch, MessageSquare
} from 'lucide-react';
import {
  useDashboardOverview,
  useActivityFeed,
  useActiveTasks,
  useNeedsHumanItems,
  useRecentResults
} from '@/lib/api/queries';

// Quick Stats Component
export function QuickStats() {
  const { data: overview, isLoading } = useDashboardOverview();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-16"></div>
          </div>
        ))}
      </div>
    );
  }

  const stats = [
    {
      label: 'Emails Today',
      value: overview?.emails.processed_today || 0,
      icon: Mail,
      color: 'blue',
      subtitle: `${overview?.emails.high_confidence || 0} high confidence`,
    },
    {
      label: 'Active Tasks',
      value: (overview?.tasks.pending || 0) + (overview?.tasks.in_progress || 0),
      icon: CheckCircle,
      color: 'green',
      subtitle: `${overview?.tasks.overdue || 0} overdue`,
    },
    {
      label: 'Needs Review',
      value: overview?.needs_human_count || 0,
      icon: AlertCircle,
      color: 'orange',
      subtitle: 'Waiting for you',
    },
    {
      label: 'Pending Decisions',
      value: overview?.decisions.pending || 0,
      icon: HelpCircle,
      color: 'purple',
      subtitle: `${overview?.questions.pending || 0} questions`,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        const colorClasses = {
          blue: 'bg-blue-50 text-blue-600',
          green: 'bg-green-50 text-green-600',
          orange: 'bg-orange-50 text-orange-600',
          purple: 'bg-purple-50 text-purple-600',
        }[stat.color];

        return (
          <div key={stat.label} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
                <p className="text-xs text-gray-500 mt-1">{stat.subtitle}</p>
              </div>
              <div className={`p-3 rounded-lg ${colorClasses}`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Active Tasks Column
export function ActiveTasksColumn() {
  const { data: tasks, isLoading } = useActiveTasks(10);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Tasks</h2>
        <div className="text-center text-gray-500 py-8">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow h-full flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Active Tasks</h2>
          <span className="text-2xl font-bold text-blue-600">{tasks?.total || 0}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tasks && tasks.items.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {tasks.items.map((task) => (
              <div key={task.task_id} className="p-4 hover:bg-gray-50 transition">
                <div className="flex items-start gap-3">
                  <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${
                    task.priority === 'urgent' ? 'bg-red-500' :
                    task.priority === 'high' ? 'bg-orange-500' :
                    task.priority === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{task.description}</p>
                    {task.email_sender && (
                      <p className="text-xs text-gray-500 mt-1">From: {task.email_sender}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2">
                      {task.deadline && (
                        <span className="inline-flex items-center gap-1 text-xs text-gray-600">
                          <Clock className="w-3 h-3" />
                          {new Date(task.deadline).toLocaleDateString('de-DE')}
                        </span>
                      )}
                      {task.status === 'in_progress' && (
                        <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                          In Progress
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>No active tasks</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Needs Human Column
export function NeedsHumanColumn() {
  const { data: runs, isLoading } = useNeedsHumanItems(10);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Needs Human</h2>
        <div className="text-center text-gray-500 py-8">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow h-full flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Needs Human</h2>
          <span className="text-2xl font-bold text-orange-600">{runs?.total || 0}</span>
        </div>
        <p className="text-sm text-gray-600 mt-1">Waiting for your review</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {runs && runs.items.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {runs.items.map((run) => (
              <Link
                key={run.run_id}
                href={`/email-agent/runs/${run.run_id}`}
                className="block p-4 hover:bg-gray-50 transition"
              >
                <div className="flex items-start gap-3">
                  <Mail className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {run.email_subject || '(No Subject)'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1 truncate">
                      From: {run.email_sender || 'Unknown'}
                    </p>
                    <div className="flex items-center gap-3 mt-2">
                      {run.category && (
                        <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                          {run.category}
                        </span>
                      )}
                      <span className="text-xs text-gray-600">
                        {run.confidence ? `${(run.confidence * 100).toFixed(0)}% conf` : 'Low conf'}
                      </span>
                    </div>
                  </div>
                  <AlertCircle className="w-4 h-4 text-orange-500 flex-shrink-0" />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>All clear!</p>
            <p className="text-xs mt-1">No items need review</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Recent Results Column
export function RecentResultsColumn() {
  const { data: results, isLoading } = useRecentResults(10);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Results</h2>
        <div className="text-center text-gray-500 py-8">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow h-full flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Results</h2>
          <span className="text-2xl font-bold text-green-600">{results?.length || 0}</span>
        </div>
        <p className="text-sm text-gray-600 mt-1">Recently processed</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {results && results.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {results.map((result) => (
              <Link
                key={result.id}
                href={`/email-agent/runs/${result.id}`}
                className="block p-4 hover:bg-gray-50 transition"
              >
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{result.title}</p>
                    <p className="text-xs text-gray-500 mt-1 truncate">{result.subtitle}</p>
                    <div className="flex items-center gap-3 mt-2">
                      {result.category && (
                        <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded">
                          {result.category}
                        </span>
                      )}
                      {result.confidence && (
                        <span className="text-xs text-gray-600">
                          {(result.confidence * 100).toFixed(0)}% confident
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        {new Date(result.timestamp).toLocaleTimeString('de-DE', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">
            <Mail className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>No recent results</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Activity Feed Component
const iconMap = {
  email: Mail,
  task: CheckCircle,
  decision: GitBranch,
  question: MessageSquare,
  user: User,
  system: Settings,
};

export function ActivityFeed() {
  const { data: activities, isLoading } = useActivityFeed({ limit: 20 });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Activity Feed</h2>
        <div className="text-center text-gray-500 py-8">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Activity Feed</h2>
          <Activity className="w-5 h-5 text-gray-400" />
        </div>
        <p className="text-sm text-gray-600 mt-1">Recent system activity</p>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {activities && activities.items.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {activities.items.map((activity) => {
              const Icon = iconMap[activity.icon_type] || Activity;

              return (
                <div key={activity.activity_id} className="p-4 hover:bg-gray-50 transition">
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 p-2 rounded-lg ${
                      activity.icon_type === 'email' ? 'bg-blue-50 text-blue-600' :
                      activity.icon_type === 'task' ? 'bg-green-50 text-green-600' :
                      activity.icon_type === 'decision' ? 'bg-orange-50 text-orange-600' :
                      activity.icon_type === 'question' ? 'bg-purple-50 text-purple-600' :
                      activity.icon_type === 'user' ? 'bg-indigo-50 text-indigo-600' :
                      'bg-gray-50 text-gray-600'
                    }`}>
                      <Icon className="w-4 h-4" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900">{activity.description}</p>

                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-gray-500">
                          {new Date(activity.timestamp).toLocaleString('de-DE', {
                            hour: '2-digit',
                            minute: '2-digit',
                            day: '2-digit',
                            month: '2-digit',
                          })}
                        </span>

                        {activity.account_id && (
                          <span className="text-xs text-gray-500">{activity.account_id}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">
            <Activity className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>No recent activity</p>
          </div>
        )}
      </div>
    </div>
  );
}
