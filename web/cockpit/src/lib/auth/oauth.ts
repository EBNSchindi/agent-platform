/**
 * OAuth Flow Handler
 * Manages OAuth popup, listens for callback, and processes authentication.
 */

import { apiClient } from '@/lib/api/client';

/**
 * Start OAuth flow for account.
 *
 * @param accountId - Account identifier (gmail_1, gmail_2, gmail_3)
 * @param authUrl - OAuth authorization URL from backend
 * @param state - CSRF state token
 * @returns Promise resolving to true if successful, false if cancelled/failed
 */
export async function startOAuthFlow(
  accountId: string,
  authUrl: string,
  state: string
): Promise<boolean> {
  return new Promise((resolve) => {
    // Calculate popup position (center of screen)
    const width = 600;
    const height = 800;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;

    // Open popup
    const popup = window.open(
      authUrl,
      'oauth-popup',
      `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,location=no,status=no`
    );

    if (!popup) {
      console.error('Popup blocked - user needs to allow popups');
      resolve(false);
      return;
    }

    // Listen for OAuth callback message
    const messageHandler = async (event: MessageEvent) => {
      // Verify message origin (should be same origin for callback page)
      if (event.origin !== window.location.origin) {
        return;
      }

      // Check message type
      if (event.data.type === 'oauth-success') {
        const { account_id, code, state: callbackState } = event.data;

        // Verify account and state match
        if (account_id === accountId && callbackState === state) {
          try {
            // Exchange code for tokens via backend
            await apiClient.post(`/auth/gmail/${accountId}/callback`, {
              code,
              state: callbackState,
            });

            // Success
            window.removeEventListener('message', messageHandler);
            resolve(true);
          } catch (err) {
            console.error('OAuth callback failed:', err);
            window.removeEventListener('message', messageHandler);
            resolve(false);
          }
        }
      } else if (event.data.type === 'oauth-error') {
        console.error('OAuth error:', event.data.error);
        window.removeEventListener('message', messageHandler);
        resolve(false);
      }
    };

    window.addEventListener('message', messageHandler);

    // Check if popup was closed manually
    const popupChecker = setInterval(() => {
      if (popup.closed) {
        clearInterval(popupChecker);
        window.removeEventListener('message', messageHandler);
        resolve(false);
      }
    }, 500);
  });
}

/**
 * Send OAuth success message to opener window.
 * Called from OAuth callback page.
 *
 * @param accountId - Account identifier
 * @param code - Authorization code from Google
 * @param state - State token
 */
export function sendOAuthSuccess(
  accountId: string,
  code: string,
  state: string
) {
  if (window.opener) {
    window.opener.postMessage(
      {
        type: 'oauth-success',
        account_id: accountId,
        code,
        state,
      },
      window.location.origin
    );
  }
}

/**
 * Send OAuth error message to opener window.
 * Called from OAuth callback page.
 *
 * @param error - Error message
 */
export function sendOAuthError(error: string) {
  if (window.opener) {
    window.opener.postMessage(
      {
        type: 'oauth-error',
        error,
      },
      window.location.origin
    );
  }
}
