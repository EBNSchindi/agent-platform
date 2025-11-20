/**
 * Review Queue Types
 *
 * Type definitions for the Review Queue system.
 * Matches backend Pydantic schemas from agent_platform/api/routes/review_queue.py
 */

export interface ReviewQueueItem {
  id: number;
  account_id: string;
  email_id: string;
  processed_email_id: number | null;
  subject: string | null;
  sender: string | null;
  snippet: string | null;
  suggested_category: string;
  importance_score: number;
  confidence: number;
  reasoning: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'modified';
  user_approved: boolean | null;
  user_corrected_category: string | null;
  user_feedback: string | null;
  added_to_queue_at: string;
  reviewed_at: string | null;
  extra_metadata: Record<string, any> | null;
}

export interface ReviewQueueListResponse {
  items: ReviewQueueItem[];
  total: number;
  pending_count: number;
  limit: number;
  offset: number;
}

export interface ReviewQueueStats {
  total_items: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  modified_count: number;
  by_category: Record<string, number>;
  avg_age_hours: number;
}

export interface ApproveRequest {
  user_feedback?: string;
  apply_action?: boolean;
}

export interface RejectRequest {
  corrected_category?: string;
  user_feedback?: string;
  apply_action?: boolean;
}

export interface ModifyRequest {
  corrected_category: string;
  user_feedback?: string;
  apply_action?: boolean;
}

export interface ActionResponse {
  success: boolean;
  message: string;
  item: ReviewQueueItem | null;
  action_applied: Record<string, any> | null;
}

// Filter types for query parameters
export interface ReviewQueueFilters {
  account_id?: string;
  status?: 'pending' | 'approved' | 'rejected' | 'modified';
  limit?: number;
  offset?: number;
}
