'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { sendOAuthSuccess, sendOAuthError } from '@/lib/auth/oauth';

function CallbackContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>(
    'processing'
  );
  const [message, setMessage] = useState('Processing authentication...');

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    // Handle error from OAuth provider
    if (error) {
      setStatus('error');
      setMessage(`Authentication failed: ${error}`);
      sendOAuthError(error);

      // Close window after 3 seconds
      setTimeout(() => {
        window.close();
      }, 3000);
      return;
    }

    // Handle success
    if (code && state) {
      // Extract account_id from state or localStorage
      // For now, we assume state contains account info or we get it from URL params
      const accountId = searchParams.get('account_id') || 'gmail_1'; // Fallback

      setStatus('success');
      setMessage('Authentication successful! You can close this window.');

      // Send success message to opener
      sendOAuthSuccess(accountId, code, state);

      // Close window after 2 seconds
      setTimeout(() => {
        window.close();
      }, 2000);
    } else {
      setStatus('error');
      setMessage('Missing authorization code or state parameter');
      sendOAuthError('Missing required parameters');

      setTimeout(() => {
        window.close();
      }, 3000);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Processing Authentication
              </h2>
              <p className="text-gray-600">{message}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Success!
              </h2>
              <p className="text-gray-600">{message}</p>
              <p className="text-sm text-gray-500 mt-4">
                This window will close automatically...
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Authentication Failed
              </h2>
              <p className="text-red-600">{message}</p>
              <p className="text-sm text-gray-500 mt-4">
                This window will close automatically...
              </p>
              <button
                onClick={() => window.close()}
                className="mt-4 px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors"
              >
                Close Window
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
