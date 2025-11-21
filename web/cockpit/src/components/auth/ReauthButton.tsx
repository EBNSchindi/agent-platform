'use client';

import { useState } from 'react';
import { Link2, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

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

  const handleGenerateLink = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Get OAuth URL from backend
      const response = await apiClient.get(
        `/auth/gmail/${accountId}/authorize`
      );

      const { auth_url } = response.data;

      // Notify parent component about OAuth URL (shows copy/open buttons)
      if (onOAuthUrlGenerated) {
        onOAuthUrlGenerated(auth_url);
      }
    } catch (err: any) {
      console.error('Failed to generate OAuth link:', err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to generate OAuth link'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleGenerateLink}
        disabled={isLoading}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating Link...
          </>
        ) : (
          <>
            <Link2 className="h-4 w-4" />
            Get OAuth Link
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
