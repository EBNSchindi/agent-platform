import { MessageSquare, Users, Clock, Loader2, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { useThreadSummary } from '@/lib/api/queries';
import { formatParticipants, getThreadAge } from '@/lib/types/threads';
import type { ThreadSummaryFilters } from '@/lib/types/threads';

interface ThreadSummaryCardProps {
  threadId: string;
  accountId: string;
}

export function ThreadSummaryCard({ threadId, accountId }: ThreadSummaryCardProps) {
  const [forceRegenerate, setForceRegenerate] = useState(false);

  const filters: ThreadSummaryFilters = {
    thread_id: threadId,
    account_id: accountId,
    force_regenerate: forceRegenerate,
  };

  const { data: summary, isLoading, error, refetch } = useThreadSummary(filters);

  const handleRegenerate = () => {
    setForceRegenerate(true);
    refetch().finally(() => setForceRegenerate(false));
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="ml-2 text-sm text-gray-600">
            {forceRegenerate ? 'Regenerating summary...' : 'Loading thread summary...'}
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-800">Failed to load thread summary</p>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Thread Summary</h3>
        <button
          onClick={handleRegenerate}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition disabled:opacity-50"
          title="Regenerate summary with LLM"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Regenerate
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Summary Text */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-gray-900 leading-relaxed">{summary.summary}</p>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* Email Count */}
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Emails</p>
              <p className="text-sm font-medium text-gray-900">{summary.email_count}</p>
            </div>
          </div>

          {/* Participants */}
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Participants</p>
              <p className="text-sm font-medium text-gray-900" title={summary.participants.join(', ')}>
                {formatParticipants(summary.participants, 2)}
              </p>
            </div>
          </div>

          {/* Thread Age */}
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Duration</p>
              <p className="text-sm font-medium text-gray-900">
                {getThreadAge(summary.started_at, summary.last_email_at)}
              </p>
            </div>
          </div>
        </div>

        {/* Email Timeline */}
        {summary.emails.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-700 mb-2">Email Timeline:</p>
            <div className="space-y-2">
              {summary.emails.map((email, index) => (
                <div
                  key={email.id || email.email_id || index}
                  className="flex items-start gap-2 text-xs"
                >
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
                    email.is_thread_start
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {email.position}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{email.sender}</p>
                    <p className="text-gray-500 truncate">{email.subject}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
