/**
 * TypeScript types for Thread API
 * Matches backend Pydantic models from agent_platform/threads/models.py
 */

export interface ThreadEmail {
  email_id: string;
  subject: string;
  sender: string;
  received_at: string;
  summary?: string | null;
  position: number;
  is_thread_start: boolean;
}

export interface ThreadSummary {
  thread_id: string;
  account_id: string;
  email_count: number;
  participants: string[];
  subject: string;
  started_at: string;
  last_email_at: string;
  summary: string;
  key_points: string[];
  emails: ThreadEmail[];
}

export interface ThreadEmailsResponse {
  thread_id: string;
  email_count: number;
  emails: Array<{
    email_id: string;
    subject: string;
    sender: string;
    received_at: string;
    category?: string;
    thread_position?: number;
    is_thread_start?: boolean;
  }>;
}

export interface ThreadSummaryFilters {
  thread_id: string;
  account_id: string;
  force_regenerate?: boolean;
}

// Helper to format participant list
export function formatParticipants(participants: string[], maxShow: number = 3): string {
  if (participants.length === 0) return 'No participants';
  if (participants.length <= maxShow) return participants.join(', ');

  const shown = participants.slice(0, maxShow).join(', ');
  const remaining = participants.length - maxShow;
  return `${shown} +${remaining} more`;
}

// Helper to get thread age
export function getThreadAge(startedAt: string, lastEmailAt: string): string {
  const start = new Date(startedAt);
  const last = new Date(lastEmailAt);
  const diffMs = last.getTime() - start.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Same day';
  if (diffDays === 1) return '1 day';
  if (diffDays < 7) return `${diffDays} days`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks`;
  return `${Math.floor(diffDays / 30)} months`;
}
