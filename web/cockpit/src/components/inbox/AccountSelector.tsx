'use client';

import { useAccounts } from '@/lib/api/queries';
import { Loader2, Mail, RefreshCw } from 'lucide-react';

interface AccountSelectorProps {
  selectedAccountId: string | null;
  onAccountChange: (accountId: string | null) => void;
}

export function AccountSelector({
  selectedAccountId,
  onAccountChange,
}: AccountSelectorProps) {
  const { data, isLoading, error, refetch } = useAccounts();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading accounts...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">
        Failed to load accounts
      </div>
    );
  }

  const accounts = data?.accounts || [];

  return (
    <div className="flex items-center gap-3">
      <Mail className="h-5 w-5 text-gray-500" />

      <select
        value={selectedAccountId || 'all'}
        onChange={(e) => {
          const value = e.target.value === 'all' ? null : e.target.value;
          onAccountChange(value);
        }}
        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
      >
        <option value="all">All Accounts ({data?.total || 0})</option>

        {accounts.map((account) => (
          <option key={account.account_id} value={account.account_id}>
            {account.email} ({account.email_count} emails)
          </option>
        ))}
      </select>

      <button
        onClick={() => refetch()}
        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        title="Refresh accounts"
      >
        <RefreshCw className="h-4 w-4" />
      </button>
    </div>
  );
}
