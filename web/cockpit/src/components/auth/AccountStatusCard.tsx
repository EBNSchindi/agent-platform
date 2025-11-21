'use client';

import { useState } from 'react';
import { Check, AlertTriangle, X, Copy, ExternalLink, RefreshCw } from 'lucide-react';
import { ReauthButton } from './ReauthButton';
import { formatDistanceToNow } from 'date-fns';

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

interface AccountStatusCardProps {
  account: AuthStatus;
  onReauthSuccess: () => void;
}

export function AccountStatusCard({
  account,
  onReauthSuccess,
}: AccountStatusCardProps) {
  const [showOAuthLink, setShowOAuthLink] = useState(false);
  const [oauthUrl, setOAuthUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Determine status color and icon
  const getStatusConfig = () => {
    if (account.authenticated && !account.needs_reauth) {
      return {
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        textColor: 'text-green-800',
        icon: <Check className="h-5 w-5 text-green-500" />,
        label: 'Active',
      };
    } else if (account.needs_reauth) {
      return {
        bgColor: 'bg-amber-50',
        borderColor: 'border-amber-200',
        textColor: 'text-amber-800',
        icon: <AlertTriangle className="h-5 w-5 text-amber-500" />,
        label: 'Re-auth Required',
      };
    } else {
      return {
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-800',
        icon: <X className="h-5 w-5 text-red-500" />,
        label: 'Not Authenticated',
      };
    }
  };

  const status = getStatusConfig();

  const handleCopyOAuthLink = async () => {
    if (!oauthUrl) return;

    try {
      await navigator.clipboard.writeText(oauthUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleOpenOAuthLink = () => {
    if (oauthUrl) {
      window.open(oauthUrl, '_blank');
    }
  };

  return (
    <div
      className={`rounded-lg border ${status.borderColor} ${status.bgColor} p-6 transition-all`}
    >
      <div className="flex items-start justify-between">
        {/* Left: Account Info */}
        <div className="flex-1">
          <div className="flex items-center gap-3">
            {status.icon}
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {account.account_id.replace('_', ' ').toUpperCase()}
              </h3>
              <p className="text-sm text-gray-600">{account.email}</p>
            </div>
          </div>

          {/* Status Details */}
          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium text-gray-700">Status:</span>
              <span className={`${status.textColor} font-medium`}>
                {status.label}
              </span>
            </div>

            {account.expires_at && (
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-gray-700">Expires:</span>
                <span className="text-gray-600">
                  {formatDistanceToNow(new Date(account.expires_at), {
                    addSuffix: true,
                  })}
                </span>
              </div>
            )}

            {account.error && (
              <div className="flex items-start gap-2 text-sm">
                <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                <span className="text-red-600">{account.error}</span>
              </div>
            )}

            {/* Technical Details */}
            <div className="flex gap-4 text-xs text-gray-500 mt-2">
              <span>
                Token:{' '}
                {account.token_exists ? (
                  <span className="text-green-600">✓</span>
                ) : (
                  <span className="text-red-600">✗</span>
                )}
              </span>
              <span>
                Credentials:{' '}
                {account.credentials_exist ? (
                  <span className="text-green-600">✓</span>
                ) : (
                  <span className="text-red-600">✗</span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex flex-col gap-2 ml-4">
          {account.needs_reauth && (
            <>
              <ReauthButton
                accountId={account.account_id}
                onSuccess={onReauthSuccess}
                onOAuthUrlGenerated={(url) => {
                  setOAuthUrl(url);
                  setShowOAuthLink(true);
                }}
              />

              {showOAuthLink && oauthUrl && (
                <div className="mt-2 space-y-2">
                  <button
                    onClick={handleCopyOAuthLink}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors w-full justify-center"
                    title="Copy OAuth URL to clipboard"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    {copied ? 'Copied!' : 'Copy OAuth Link'}
                  </button>

                  <button
                    onClick={handleOpenOAuthLink}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-blue-700 bg-white border border-blue-300 rounded hover:bg-blue-50 transition-colors w-full justify-center"
                    title="Open OAuth URL in new tab"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Open Link
                  </button>
                </div>
              )}
            </>
          )}

          {account.authenticated && !account.needs_reauth && (
            <div className="flex items-center gap-2 text-sm text-green-600 font-medium">
              <Check className="h-4 w-4" />
              Connected
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
