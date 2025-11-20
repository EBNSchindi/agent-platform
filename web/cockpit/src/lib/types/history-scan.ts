/**
 * TypeScript types for History Scan API
 * Matches backend Pydantic models from agent_platform/history_scan/models.py
 */

export type ScanStatus = 'not_started' | 'in_progress' | 'paused' | 'completed' | 'failed';

export interface ScanConfig {
  account_id: string;
  batch_size?: number;
  max_results?: number | null;
  query?: string;
  skip_already_processed?: boolean;
  process_attachments?: boolean;
  process_threads?: boolean;
}

export interface ScanProgress {
  scan_id: string;
  account_id: string;
  status: ScanStatus;

  // Progress counters
  total_found: number;
  processed: number;
  skipped: number;
  failed: number;

  // Classification breakdown
  classified_high: number;
  classified_medium: number;
  classified_low: number;

  // Extraction stats
  tasks_extracted: number;
  decisions_extracted: number;
  questions_extracted: number;

  // Attachment & thread stats
  attachments_downloaded: number;
  threads_summarized: number;

  // Timing
  started_at: string;
  last_updated_at: string;
  completed_at: string | null;
  estimated_completion: string | null;

  // Resume capability
  last_processed_email_id: string | null;
  next_page_token: string | null;

  // Error tracking
  error_message: string | null;
  error_details: Record<string, any> | null;
}

export interface ScanResult {
  scan_id: string;
  account_id: string;
  status: ScanStatus;

  // Summary stats
  total_processed: number;
  total_skipped: number;
  total_failed: number;

  // Time taken
  duration_seconds: number;
  emails_per_second: number;

  // Classification summary
  high_confidence: number;
  medium_confidence: number;
  low_confidence: number;

  // Extraction summary
  total_tasks: number;
  total_decisions: number;
  total_questions: number;

  // Attachment & thread summary
  total_attachments: number;
  total_threads: number;

  // Error summary
  errors: Array<Record<string, any>>;
}

// Helper to calculate progress percentage
export function calculateProgress(progress: ScanProgress): number {
  if (progress.total_found === 0) return 0;
  return Math.round((progress.processed / progress.total_found) * 100);
}

// Helper to format duration
export function formatDuration(startedAt: string, completedAt?: string | null): string {
  const start = new Date(startedAt);
  const end = completedAt ? new Date(completedAt) : new Date();
  const diffSeconds = Math.floor((end.getTime() - start.getTime()) / 1000);

  if (diffSeconds < 60) return `${diffSeconds}s`;
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ${diffSeconds % 60}s`;
  const hours = Math.floor(diffSeconds / 3600);
  const minutes = Math.floor((diffSeconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

// Helper to get status color
export function getStatusColor(status: ScanStatus): string {
  const colorMap: Record<ScanStatus, string> = {
    not_started: 'bg-gray-100 text-gray-800 border-gray-300',
    in_progress: 'bg-blue-100 text-blue-800 border-blue-300',
    paused: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    completed: 'bg-green-100 text-green-800 border-green-300',
    failed: 'bg-red-100 text-red-800 border-red-300',
  };
  return colorMap[status] || 'bg-gray-100 text-gray-800 border-gray-300';
}

// Helper to get status label
export function getStatusLabel(status: ScanStatus): string {
  const labelMap: Record<ScanStatus, string> = {
    not_started: 'Not Started',
    in_progress: 'In Progress',
    paused: 'Paused',
    completed: 'Completed',
    failed: 'Failed',
  };
  return labelMap[status] || status;
}

// Helper to format ETA
export function formatETA(estimatedCompletion: string | null): string {
  if (!estimatedCompletion) return 'Calculating...';

  const eta = new Date(estimatedCompletion);
  const now = new Date();
  const diffMs = eta.getTime() - now.getTime();

  if (diffMs <= 0) return 'Soon';

  const diffMinutes = Math.floor(diffMs / 1000 / 60);
  if (diffMinutes < 1) return '< 1 min';
  if (diffMinutes < 60) return `~${diffMinutes} min`;

  const diffHours = Math.floor(diffMinutes / 60);
  return `~${diffHours}h ${diffMinutes % 60}m`;
}
