'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { useAcceptRun, useRejectRun } from '@/lib/api/queries';

interface HITLActionsProps {
  runId: string;
  currentCategory: string | null;
  confidence: number | null;
  status: string;
}

export function HITLActions({
  runId,
  currentCategory,
  confidence,
  status,
}: HITLActionsProps) {
  const router = useRouter();
  const [feedback, setFeedback] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);

  const acceptMutation = useAcceptRun();
  const rejectMutation = useRejectRun();

  const isAlreadyActioned = status === 'accepted' || status === 'rejected';
  const isLoading = acceptMutation.isPending || rejectMutation.isPending;

  const handleAccept = async () => {
    try {
      await acceptMutation.mutateAsync({
        runId,
        feedback: feedback.trim() || undefined,
      });
      setShowSuccess(true);
      setTimeout(() => {
        router.push('/email-agent');
      }, 1500);
    } catch (error) {
      console.error('Accept failed:', error);
    }
  };

  const handleReject = async () => {
    if (!feedback.trim()) {
      alert('Bitte geben Sie einen Grund für die Ablehnung an.');
      return;
    }

    try {
      await rejectMutation.mutateAsync({
        runId,
        feedback: feedback.trim(),
      });
      setShowSuccess(true);
      setTimeout(() => {
        router.push('/email-agent');
      }, 1500);
    } catch (error) {
      console.error('Reject failed:', error);
    }
  };

  if (showSuccess) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-8">
          <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-600" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Feedback gespeichert!
          </h3>
          <p className="text-sm text-gray-600">
            Weiterleitung zur Übersicht...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow sticky top-6">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Your Feedback</h2>
        {currentCategory && confidence !== null && (
          <div className="mt-3 text-sm text-gray-600">
            <p>
              Klassifiziert als:{' '}
              <span className="font-medium">{currentCategory}</span>
            </p>
            <p>
              Confidence: <span className="font-medium">{(confidence * 100).toFixed(0)}%</span>
            </p>
          </div>
        )}
      </div>

      <div className="p-6 space-y-4">
        {isAlreadyActioned ? (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <p className="text-sm text-blue-900 font-medium">
              Diese Run wurde bereits als "{status}" markiert.
            </p>
          </div>
        ) : (
          <>
            {/* Feedback Textarea */}
            <div>
              <label htmlFor="feedback" className="block text-sm font-medium text-gray-700 mb-2">
                Feedback (optional für Accept, erforderlich für Reject)
              </label>
              <textarea
                id="feedback"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Zusätzliche Anmerkungen oder Korrekturen..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                rows={4}
                disabled={isLoading}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-3">
              <button
                onClick={handleAccept}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {acceptMutation.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Wird akzeptiert...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    Accept Classification
                  </>
                )}
              </button>

              <button
                onClick={handleReject}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {rejectMutation.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Wird abgelehnt...
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5" />
                    Reject Classification
                  </>
                )}
              </button>
            </div>

            {/* Error Messages */}
            {acceptMutation.isError && (
              <div className="bg-red-50 border border-red-200 rounded p-3">
                <p className="text-sm text-red-900">
                  Fehler beim Akzeptieren. Bitte versuchen Sie es erneut.
                </p>
              </div>
            )}

            {rejectMutation.isError && (
              <div className="bg-red-50 border border-red-200 rounded p-3">
                <p className="text-sm text-red-900">
                  Fehler beim Ablehnen. Bitte versuchen Sie es erneut.
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Info Box */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        <p className="text-xs text-gray-600">
          Ihr Feedback hilft dem System, zukünftige Klassifizierungen zu verbessern.
        </p>
      </div>
    </div>
  );
}
