'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { AccountStatusCard } from '@/components/auth/AccountStatusCard';
import { Loader2 } from 'lucide-react';

interface AuthStatus {
  account_id: string;
  email: string;
  authenticated: boolean;
  token_exists: boolean;
  credentials_exist: boolean;
  expires_at: string | null;
  needs_reauth: boolean;
  error: string | null;
}

interface AccountsResponse {
  accounts: AuthStatus[];
  total: number;
  authenticated_count: number;
  needs_reauth_count: number;
}

export default function SettingsPage() {
  // Fetch account statuses
  const { data, isLoading, error, refetch } = useQuery<AccountsResponse>({
    queryKey: ['auth-accounts'],
    queryFn: async () => {
      const response = await apiClient.get('/auth/accounts');
      return response.data;
    },
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-medium">Error Loading Accounts</h3>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  const needsReauth = data && data.needs_reauth_count > 0;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Account Settings</h1>
        <p className="text-gray-600 mt-2">
          Manage your email account connections and authentication
        </p>
      </div>

      {/* Global Warning */}
      {needsReauth && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-amber-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-amber-800">
                Re-authentication Required
              </h3>
              <p className="text-sm text-amber-700 mt-1">
                {data.needs_reauth_count} account(s) need re-authentication to
                continue working properly.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-sm font-medium text-gray-500">Total Accounts</div>
          <div className="mt-2 text-3xl font-bold text-gray-900">
            {data?.total || 0}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-sm font-medium text-gray-500">Authenticated</div>
          <div className="mt-2 text-3xl font-bold text-green-600">
            {data?.authenticated_count || 0}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-sm font-medium text-gray-500">Needs Attention</div>
          <div className="mt-2 text-3xl font-bold text-amber-600">
            {data?.needs_reauth_count || 0}
          </div>
        </div>
      </div>

      {/* Account List */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Email Accounts
        </h2>

        <div className="space-y-4">
          {data?.accounts.map((account) => (
            <AccountStatusCard
              key={account.account_id}
              account={account}
              onReauthSuccess={() => refetch()}
            />
          ))}
        </div>
      </div>

      {/* Help Section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-blue-900 mb-2">
          Need Help?
        </h3>
        <div className="text-sm text-blue-800 space-y-2">
          <p>
            <strong>Re-authentication:</strong> Click "Re-authenticate" button to
            reconnect your account. You'll be redirected to Google for
            authorization.
          </p>
          <p>
            <strong>Token Expiry:</strong> Access tokens expire after 1 hour but
            are automatically refreshed. Re-authentication is only needed if the
            refresh token expires (typically after 6 months of inactivity).
          </p>
          <p>
            <strong>Manual OAuth:</strong> Use "Copy OAuth Link" to get the
            authorization URL if the popup doesn't work.
          </p>
        </div>
      </div>
    </div>
  );
}
