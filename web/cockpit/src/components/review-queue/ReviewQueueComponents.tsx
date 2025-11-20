'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  CheckCircle,
  XCircle,
  Edit3,
  Mail,
  User,
  Calendar,
  TrendingUp,
  Loader2,
  AlertCircle,
  Info,
} from 'lucide-react';
import type { ReviewQueueItem, ReviewQueueStats as StatsType } from '@/lib/types/review-queue';
import {
  useApproveReviewItem,
  useRejectReviewItem,
  useModifyReviewItem,
  useReviewQueueStats,
} from '@/lib/api/queries';

// ============================================================================
// ReviewQueueCard - Displays single review queue item with actions
// ============================================================================

interface ReviewQueueCardProps {
  item: ReviewQueueItem;
  onActionComplete?: () => void;
}

export function ReviewQueueCard({ item, onActionComplete }: ReviewQueueCardProps) {
  const router = useRouter();
  const [showReclassifyModal, setShowReclassifyModal] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [applyAction, setApplyAction] = useState(false);

  const approveMutation = useApproveReviewItem();
  const rejectMutation = useRejectReviewItem();

  const isLoading = approveMutation.isPending || rejectMutation.isPending;
  const isActioned = item.status !== 'pending';

  const handleApprove = async () => {
    try {
      await approveMutation.mutateAsync({
        itemId: item.id,
        userFeedback: feedback.trim() || undefined,
        applyAction,
      });
      onActionComplete?.();
    } catch (error) {
      console.error('Approve failed:', error);
    }
  };

  const handleReject = async () => {
    try {
      await rejectMutation.mutateAsync({
        itemId: item.id,
        userFeedback: feedback.trim() || undefined,
        applyAction,
      });
      onActionComplete?.();
    } catch (error) {
      console.error('Reject failed:', error);
    }
  };

  // Category badge color
  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      wichtig: 'bg-red-100 text-red-800 border-red-200',
      action_required: 'bg-orange-100 text-orange-800 border-orange-200',
      nice_to_know: 'bg-blue-100 text-blue-800 border-blue-200',
      newsletter: 'bg-purple-100 text-purple-800 border-purple-200',
      spam: 'bg-gray-100 text-gray-800 border-gray-200',
      system_notifications: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    };
    return colors[category] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  // Confidence indicator color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.85) return 'text-green-600';
    if (confidence >= 0.70) return 'text-yellow-600';
    return 'text-orange-600';
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow border border-gray-200 hover:shadow-md transition">
        {/* Header with status */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {item.subject || '(No Subject)'}
              </h3>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  <span className="truncate">{item.sender || 'Unknown'}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  <span>{new Date(item.added_to_queue_at).toLocaleDateString('de-DE')}</span>
                </div>
              </div>
            </div>

            {/* Status badge */}
            {isActioned && (
              <div className="ml-4">
                {item.status === 'approved' && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                    <CheckCircle className="w-3 h-3" />
                    Approved
                  </span>
                )}
                {item.status === 'rejected' && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
                    <XCircle className="w-3 h-3" />
                    Rejected
                  </span>
                )}
                {item.status === 'modified' && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                    <Edit3 className="w-3 h-3" />
                    Modified
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          {/* Email snippet */}
          {item.snippet && (
            <p className="text-sm text-gray-700 line-clamp-2">{item.snippet}</p>
          )}

          {/* Classification info */}
          <div className="flex items-center gap-3 flex-wrap">
            <div>
              <span className="text-xs text-gray-500">Suggested Category:</span>
              <span className={`ml-2 inline-block px-2 py-1 text-xs font-medium rounded border ${getCategoryColor(item.suggested_category)}`}>
                {item.suggested_category}
              </span>
            </div>
            <div>
              <span className="text-xs text-gray-500">Confidence:</span>
              <span className={`ml-2 font-semibold text-sm ${getConfidenceColor(item.confidence)}`}>
                {(item.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div>
              <span className="text-xs text-gray-500">Importance:</span>
              <span className="ml-2 font-semibold text-sm text-gray-900">
                {(item.importance_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Reasoning */}
          {item.reasoning && (
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer hover:text-gray-900 font-medium">
                Show reasoning
              </summary>
              <p className="mt-2 pl-4 border-l-2 border-gray-200">{item.reasoning}</p>
            </details>
          )}

          {/* User correction info */}
          {item.user_corrected_category && (
            <div className="bg-blue-50 border border-blue-200 rounded p-2 text-xs">
              <span className="font-medium text-blue-900">Corrected to:</span>{' '}
              <span className="text-blue-700">{item.user_corrected_category}</span>
            </div>
          )}
        </div>

        {/* Actions (only if pending) */}
        {!isActioned && (
          <div className="p-4 border-t border-gray-200 bg-gray-50 space-y-3">
            {/* Feedback textarea */}
            <div>
              <label htmlFor={`feedback-${item.id}`} className="block text-xs font-medium text-gray-700 mb-1">
                Optional Feedback
              </label>
              <textarea
                id={`feedback-${item.id}`}
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Add comments or corrections..."
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                rows={2}
                disabled={isLoading}
              />
            </div>

            {/* Apply action checkbox */}
            <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={applyAction}
                onChange={(e) => setApplyAction(e.target.checked)}
                disabled={isLoading}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Apply Gmail actions (label, archive, mark-read)</span>
            </label>

            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleApprove}
                disabled={isLoading}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {approveMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Approving...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4" />
                    Approve
                  </>
                )}
              </button>

              <button
                onClick={() => setShowReclassifyModal(true)}
                disabled={isLoading}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Edit3 className="w-4 h-4" />
                Reclassify
              </button>

              <button
                onClick={handleReject}
                disabled={isLoading}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {rejectMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Rejecting...
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4" />
                    Reject
                  </>
                )}
              </button>
            </div>

            {/* Error messages */}
            {(approveMutation.isError || rejectMutation.isError) && (
              <div className="bg-red-50 border border-red-200 rounded p-2">
                <p className="text-xs text-red-900">
                  Action failed. Please try again.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Reclassify Modal */}
      {showReclassifyModal && (
        <ReclassifyModal
          item={item}
          initialFeedback={feedback}
          initialApplyAction={applyAction}
          onClose={() => setShowReclassifyModal(false)}
          onSuccess={() => {
            setShowReclassifyModal(false);
            onActionComplete?.();
          }}
        />
      )}
    </>
  );
}

// ============================================================================
// ReviewQueueStats - Displays queue statistics
// ============================================================================

interface ReviewQueueStatsProps {
  accountId?: string;
}

export function ReviewQueueStats({ accountId }: ReviewQueueStatsProps) {
  const { data: stats, isLoading } = useReviewQueueStats(accountId);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-32 mb-4"></div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-4 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-sm text-gray-500">No statistics available</p>
      </div>
    );
  }

  const statItems = [
    {
      label: 'Total Items',
      value: stats.total_items,
      color: 'text-gray-900',
    },
    {
      label: 'Pending Review',
      value: stats.pending_count,
      color: 'text-orange-600',
      highlight: stats.pending_count > 0,
    },
    {
      label: 'Approved',
      value: stats.approved_count,
      color: 'text-green-600',
    },
    {
      label: 'Rejected',
      value: stats.rejected_count,
      color: 'text-red-600',
    },
    {
      label: 'Modified',
      value: stats.modified_count,
      color: 'text-blue-600',
    },
  ];

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          Queue Statistics
        </h3>
      </div>

      <div className="p-4 space-y-3">
        {/* Summary stats */}
        <div className="grid grid-cols-2 gap-3">
          {statItems.map((stat) => (
            <div
              key={stat.label}
              className={`p-3 rounded-lg ${
                stat.highlight ? 'bg-orange-50 border border-orange-200' : 'bg-gray-50'
              }`}
            >
              <p className="text-xs text-gray-600">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.color} mt-1`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Average age */}
        {stats.avg_age_hours > 0 && (
          <div className="pt-3 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Avg. Age:</span>
              <span className="font-semibold text-gray-900">
                {stats.avg_age_hours.toFixed(1)}h
              </span>
            </div>
          </div>
        )}

        {/* By category breakdown */}
        {Object.keys(stats.by_category).length > 0 && (
          <div className="pt-3 border-t border-gray-200">
            <p className="text-xs font-medium text-gray-700 mb-2">By Category:</p>
            <div className="space-y-1">
              {Object.entries(stats.by_category)
                .sort(([, a], [, b]) => b - a)
                .map(([category, count]) => (
                  <div key={category} className="flex items-center justify-between text-xs">
                    <span className="text-gray-600 capitalize">{category.replace('_', ' ')}</span>
                    <span className="font-semibold text-gray-900">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// ReclassifyModal - Modal for reclassifying email
// ============================================================================

interface ReclassifyModalProps {
  item: ReviewQueueItem;
  initialFeedback?: string;
  initialApplyAction?: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ReclassifyModal({
  item,
  initialFeedback = '',
  initialApplyAction = true,
  onClose,
  onSuccess,
}: ReclassifyModalProps) {
  const [correctedCategory, setCorrectedCategory] = useState(item.suggested_category);
  const [feedback, setFeedback] = useState(initialFeedback);
  const [applyAction, setApplyAction] = useState(initialApplyAction);

  const modifyMutation = useModifyReviewItem();

  const categories = [
    { value: 'wichtig', label: '🔴 Wichtig', description: 'Important emails requiring attention' },
    { value: 'action_required', label: '⚡ Action Required', description: 'Tasks or actions needed' },
    { value: 'nice_to_know', label: '📘 Nice to Know', description: 'Informational content' },
    { value: 'newsletter', label: '📰 Newsletter', description: 'Newsletters and updates' },
    { value: 'spam', label: '🗑️ Spam', description: 'Unwanted emails' },
    { value: 'system_notifications', label: '🔔 System', description: 'Automated notifications' },
  ];

  const handleSubmit = async () => {
    if (correctedCategory === item.suggested_category) {
      alert('Please select a different category to reclassify.');
      return;
    }

    try {
      await modifyMutation.mutateAsync({
        itemId: item.id,
        correctedCategory,
        userFeedback: feedback.trim() || undefined,
        applyAction,
      });
      onSuccess();
    } catch (error) {
      console.error('Modify failed:', error);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Reclassify Email</h2>
          <p className="text-sm text-gray-600 mt-1">
            Select the correct category for this email
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Current classification info */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm">
            <p className="text-gray-700">
              <span className="font-medium">Current:</span> {item.suggested_category}
            </p>
            <p className="text-gray-700 mt-1">
              <span className="font-medium">Confidence:</span> {(item.confidence * 100).toFixed(0)}%
            </p>
          </div>

          {/* Category selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Correct Category
            </label>
            <div className="space-y-2">
              {categories.map((cat) => (
                <label
                  key={cat.value}
                  className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition ${
                    correctedCategory === cat.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="radio"
                    value={cat.value}
                    checked={correctedCategory === cat.value}
                    onChange={(e) => setCorrectedCategory(e.target.value)}
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{cat.label}</p>
                    <p className="text-xs text-gray-600">{cat.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Feedback */}
          <div>
            <label htmlFor="modal-feedback" className="block text-sm font-medium text-gray-700 mb-1">
              Optional Feedback
            </label>
            <textarea
              id="modal-feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Explain why this category is more appropriate..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              rows={3}
              disabled={modifyMutation.isPending}
            />
          </div>

          {/* Apply action checkbox */}
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              checked={applyAction}
              onChange={(e) => setApplyAction(e.target.checked)}
              disabled={modifyMutation.isPending}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Apply Gmail actions with corrected category</span>
          </label>

          {/* Error message */}
          {modifyMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded p-3">
              <p className="text-sm text-red-900">Failed to reclassify. Please try again.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 flex gap-3">
          <button
            onClick={onClose}
            disabled={modifyMutation.isPending}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={modifyMutation.isPending || correctedCategory === item.suggested_category}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {modifyMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4" />
                Save
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
