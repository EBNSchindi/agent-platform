import { Play, Pause, X, Clock, Mail, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useScanProgress, usePauseScan, useResumeScan, useCancelScan } from '@/lib/api/queries';
import {
  calculateProgress,
  formatDuration,
  getStatusColor,
  getStatusLabel,
  formatETA,
} from '@/lib/types/history-scan';
import type { ScanProgress } from '@/lib/types/history-scan';

interface ScanProgressCardProps {
  scanId: string;
}

export function ScanProgressCard({ scanId }: ScanProgressCardProps) {
  const { data: progress, isLoading } = useScanProgress(scanId);
  const pauseScan = usePauseScan();
  const resumeScan = useResumeScan();
  const cancelScan = useCancelScan();

  if (isLoading || !progress) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="ml-2 text-sm text-gray-600">Loading scan progress...</span>
        </div>
      </div>
    );
  }

  const progressPercent = calculateProgress(progress);
  const isActive = progress.status === 'in_progress';
  const isPaused = progress.status === 'paused';
  const isCompleted = progress.status === 'completed';
  const isFailed = progress.status === 'failed';

  const handlePause = async () => {
    await pauseScan.mutateAsync(scanId);
  };

  const handleResume = async () => {
    await resumeScan.mutateAsync(scanId);
  };

  const handleCancel = async () => {
    if (confirm('Are you sure you want to cancel this scan?')) {
      await cancelScan.mutateAsync(scanId);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">History Scan</h3>
          <p className="text-sm text-gray-500">{progress.account_id}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(progress.status)}`}>
            {getStatusLabel(progress.status)}
          </span>

          {/* Control Buttons */}
          <div className="flex gap-1">
            {isActive && (
              <button
                onClick={handlePause}
                disabled={pauseScan.isPending}
                className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition disabled:opacity-50"
                title="Pause scan"
              >
                <Pause className="w-4 h-4" />
              </button>
            )}

            {isPaused && (
              <button
                onClick={handleResume}
                disabled={resumeScan.isPending}
                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition disabled:opacity-50"
                title="Resume scan"
              >
                <Play className="w-4 h-4" />
              </button>
            )}

            {(isActive || isPaused) && (
              <button
                onClick={handleCancel}
                disabled={cancelScan.isPending}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition disabled:opacity-50"
                title="Cancel scan"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {progress.processed} / {progress.total_found} emails
          </span>
          <span className="text-sm font-medium text-gray-700">{progressPercent}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${
              isFailed ? 'bg-red-600' : isCompleted ? 'bg-green-600' : 'bg-blue-600'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* ETA */}
        {isActive && progress.estimated_completion && (
          <div className="mt-2 flex items-center gap-1 text-xs text-gray-500">
            <Clock className="w-3 h-3" />
            <span>ETA: {formatETA(progress.estimated_completion)}</span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Processed */}
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Processed</p>
          <p className="text-2xl font-bold text-green-600">{progress.processed}</p>
        </div>

        {/* Skipped */}
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Skipped</p>
          <p className="text-2xl font-bold text-gray-600">{progress.skipped}</p>
        </div>

        {/* Failed */}
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Failed</p>
          <p className="text-2xl font-bold text-red-600">{progress.failed}</p>
        </div>

        {/* Tasks */}
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Tasks</p>
          <p className="text-2xl font-bold text-blue-600">{progress.tasks_extracted}</p>
        </div>
      </div>

      {/* Classification Breakdown */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-sm font-medium text-gray-700 mb-3">Classification Results</p>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-green-50 p-3 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-xs font-medium text-green-900">High</span>
            </div>
            <p className="text-lg font-bold text-green-900">{progress.classified_high}</p>
          </div>

          <div className="bg-yellow-50 p-3 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle className="w-4 h-4 text-yellow-600" />
              <span className="text-xs font-medium text-yellow-900">Medium</span>
            </div>
            <p className="text-lg font-bold text-yellow-900">{progress.classified_medium}</p>
          </div>

          <div className="bg-red-50 p-3 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <span className="text-xs font-medium text-red-900">Low</span>
            </div>
            <p className="text-lg font-bold text-red-900">{progress.classified_low}</p>
          </div>
        </div>
      </div>

      {/* Extraction Stats */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-sm font-medium text-gray-700 mb-3">Extracted Items</p>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-xs text-gray-500">Tasks</p>
            <p className="text-lg font-semibold text-gray-900">{progress.tasks_extracted}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Decisions</p>
            <p className="text-lg font-semibold text-gray-900">{progress.decisions_extracted}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Questions</p>
            <p className="text-lg font-semibold text-gray-900">{progress.questions_extracted}</p>
          </div>
        </div>
      </div>

      {/* Timing */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <div>
            <span className="font-medium">Started:</span>{' '}
            {new Date(progress.started_at).toLocaleString()}
          </div>
          <div>
            <span className="font-medium">Duration:</span>{' '}
            {formatDuration(progress.started_at, progress.completed_at)}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {isFailed && progress.error_message && (
        <div className="p-4 border-t border-red-200 bg-red-50">
          <p className="text-sm font-medium text-red-900 mb-1">Error:</p>
          <p className="text-xs text-red-700">{progress.error_message}</p>
        </div>
      )}
    </div>
  );
}
