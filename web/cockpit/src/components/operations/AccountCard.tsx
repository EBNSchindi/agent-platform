'use client';

import { useState } from 'react';
import { useEmails } from '@/lib/api/queries';
import { Mail, CheckCircle, XCircle, Loader2, TestTube, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface Account {
  account_id: string;
  email: string;
  account_type: string;
  has_token: boolean;
  last_seen: string | null;
  email_count: number;
}

interface AccountCardProps {
  account: Account;
}

export function AccountCard({ account }: AccountCardProps) {
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  // Fetch 5 latest emails for this account
  const { data: emailsData, isLoading: emailsLoading } = useEmails({
    account_id: account.account_id,
    limit: 5,
  });

  const emails = emailsData?.emails || [];

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await fetch(`/api/accounts/${account.account_id}/test`, {
        method: 'POST',
      });
      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Connection test failed',
        error: String(error),
      });
    } finally {
      setIsTesting(false);
    }
  };

  const statusColor = account.has_token ? 'text-green-600' : 'text-yellow-600';
  const statusBg = account.has_token ? 'bg-green-100' : 'bg-yellow-100';
  const StatusIcon = account.has_token ? CheckCircle : XCircle;

  return (
    <div className="border rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow">
      {/* Account Header */}
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900">{account.account_id}</h3>
              <span className={`px-2 py-0.5 text-xs rounded-full ${statusBg} ${statusColor} flex items-center gap-1`}>
                <StatusIcon className="w-3 h-3" />
                {account.has_token ? 'Online' : 'Offline'}
              </span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">
                {account.account_type}
              </span>
            </div>
            <p className="text-sm text-gray-600">{account.email}</p>
            <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
              <span>{account.email_count} emails</span>
              {account.last_seen && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDistanceToNow(new Date(account.last_seen), { addSuffix: true })}
                </span>
              )}
            </div>
          </div>

          <button
            onClick={handleTestConnection}
            disabled={isTesting}
            className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {isTesting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <TestTube className="w-4 h-4" />
                Test
              </>
            )}
          </button>
        </div>

        {/* Test Result */}
        {testResult && (
          <div className={`mt-3 p-2 rounded text-sm ${testResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            <p className="font-medium">{testResult.message}</p>
            {testResult.latency_ms && (
              <p className="text-xs mt-1">Latency: {testResult.latency_ms.toFixed(0)}ms</p>
            )}
          </div>
        )}
      </div>

      {/* Recent Emails (5 latest) */}
      <div className="p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
          <Mail className="w-4 h-4" />
          Recent Emails (5 latest)
        </h4>

        {emailsLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : emails.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">No emails found</p>
        ) : (
          <div className="space-y-2">
            {emails.map((email) => (
              <div
                key={email.id || email.email_id}
                className="p-3 border rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {email.subject || '(No Subject)'}
                    </p>
                    <p className="text-xs text-gray-500 truncate mt-0.5">
                      {email.sender}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {email.category && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700">
                        {email.category}
                      </span>
                    )}
                    {email.received_at && (
                      <span className="text-xs text-gray-400">
                        {formatDistanceToNow(new Date(email.received_at), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
