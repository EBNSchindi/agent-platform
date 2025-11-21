'use client';

import { useState } from 'react';
import { LogIn, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { startOAuthFlow } from '@/lib/auth/oauth';

interface ReauthButtonProps {
  accountId: string;
  onSuccess: () => void;
  onOAuthUrlGenerated?: (url: string) => void;
}

export function ReauthButton({
  accountId,
  onSuccess,
  onOAuthUrlGenerated,
}: ReauthButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleReauth = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Step 1: Get OAuth URL from backend
      const response = await apiClient.get(
        `/auth/gmail/${accountId}/authorize`
      );

      const { auth_url, state } = response.data;

      // Notify parent component about OAuth URL
      if (onOAuthUrlGenerated) {
        onOAuthUrlGenerated(auth_url);
      }

      // Step 2: Start OAuth flow (opens popup)
      const success = await startOAuthFlow(accountId, auth_url, state);

      if (success) {
        // Success - notify parent
        onSuccess();
      } else {
        setError('Authentication was cancelled or failed');
      }
    } catch (err: any) {
      console.error('Re-authentication error:', err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to start authentication'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleReauth}
        disabled={isLoading}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Authenticating...
          </>
        ) : (
          <>
            <LogIn className="h-4 w-4" />
            Re-authenticate
          </>
        )}
      </button>

      {error && (
        <div className="mt-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
          {error}
        </div>
      )}
    </div>
  );
}
