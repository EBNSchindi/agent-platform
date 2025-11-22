'use client';

import { useAccounts } from '@/lib/api/queries';
import { AccountCard } from './AccountCard';
import { AlertCircle, Loader2 } from 'lucide-react';

export function AccountsTab() {
  const { data: accountsData, isLoading, error } = useAccounts();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        <span className="ml-3 text-gray-600">Loading accounts...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
        <AlertCircle className="w-5 h-5 text-red-500" />
        <div>
          <p className="font-medium text-red-900">Failed to load accounts</p>
          <p className="text-sm text-red-700">{error.message}</p>
        </div>
      </div>
    );
  }

  const accounts = accountsData?.accounts || [];

  if (accounts.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">No email accounts found</p>
        <p className="text-sm text-gray-500 mt-2">
          Configure accounts in .env file
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Email Accounts</h2>
        <p className="text-sm text-gray-600 mt-1">
          {accounts.length} account{accounts.length !== 1 ? 's' : ''} configured
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {accounts.map((account) => (
          <AccountCard key={account.account_id} account={account} />
        ))}
      </div>
    </div>
  );
}
