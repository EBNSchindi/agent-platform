import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  EmailAgentStatus,
  RunsListResponse,
  RunDetail,
} from '../types/email-agent';
import type {
  DashboardOverview,
  TodaySummary,
  ActivityFeedResponse,
  TaskItem,
  RecentResult,
} from '../types/dashboard';
import type {
  ReviewQueueItem,
  ReviewQueueListResponse,
  ReviewQueueStats,
  ReviewQueueFilters,
  ApproveRequest,
  RejectRequest,
  ModifyRequest,
  ActionResponse,
} from '../types/review-queue';
import type {
  AttachmentMetadata,
  AttachmentListResponse,
  AttachmentFilters,
} from '../types/attachments';
import type {
  ThreadSummary,
  ThreadEmailsResponse,
  ThreadSummaryFilters,
} from '../types/threads';

// ============================================================================
// Email-Agent Queries
// ============================================================================

export const useEmailAgentStatus = () => {
  return useQuery({
    queryKey: ['email-agent', 'status'],
    queryFn: async () => {
      const { data } = await apiClient.get<EmailAgentStatus>('/email-agent/status');
      return data;
    },
    refetchInterval: 10000, // Refresh every 10s
  });
};

export const useEmailAgentRuns = (filters?: {
  limit?: number;
  offset?: number;
  needs_human?: boolean;
}) => {
  return useQuery({
    queryKey: ['email-agent', 'runs', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<RunsListResponse>('/email-agent/runs', {
        params: filters,
      });
      return data;
    },
  });
};

export const useRun = (runId: string) => {
  return useQuery({
    queryKey: ['runs', runId],
    queryFn: async () => {
      const { data } = await apiClient.get<RunDetail>(`/email-agent/runs/${runId}`);
      return data;
    },
    enabled: !!runId,
  });
};

// ============================================================================
// Email-Agent Mutations
// ============================================================================

export const useAcceptRun = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ runId, feedback }: { runId: string; feedback?: string }) => {
      const { data } = await apiClient.post(`/email-agent/runs/${runId}/accept`, {
        feedback,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-agent'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

export const useRejectRun = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ runId, feedback }: { runId: string; feedback?: string }) => {
      const { data } = await apiClient.post(`/email-agent/runs/${runId}/reject`, {
        feedback,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-agent'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
};

// ============================================================================
// Dashboard Queries
// ============================================================================

export const useDashboardOverview = () => {
  return useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardOverview>('/dashboard/overview');
      return data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
};

export const useTodaySummary = () => {
  return useQuery({
    queryKey: ['dashboard', 'today'],
    queryFn: async () => {
      const { data } = await apiClient.get<TodaySummary>('/dashboard/today');
      return data;
    },
    refetchInterval: 60000, // Refresh every 60s
  });
};

export const useActivityFeed = (filters?: { limit?: number; offset?: number }) => {
  return useQuery({
    queryKey: ['dashboard', 'activity', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<ActivityFeedResponse>('/dashboard/activity', {
        params: filters,
      });
      return data;
    },
    refetchInterval: 10000, // Refresh every 10s
  });
};

export const useActiveTasks = (limit: number = 10) => {
  return useQuery({
    queryKey: ['dashboard', 'active-tasks', limit],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: TaskItem[]; total: number }>('/tasks', {
        params: {
          status: 'pending,in_progress',
          limit,
          offset: 0,
        },
      });
      return data;
    },
    refetchInterval: 15000, // Refresh every 15s
  });
};

export const useNeedsHumanItems = (limit: number = 10) => {
  return useQuery({
    queryKey: ['dashboard', 'needs-human', limit],
    queryFn: async () => {
      const { data } = await apiClient.get<RunsListResponse>('/email-agent/runs', {
        params: {
          needs_human: true,
          limit,
          offset: 0,
        },
      });
      return data;
    },
    refetchInterval: 15000, // Refresh every 15s
  });
};

export const useRecentResults = (limit: number = 10) => {
  return useQuery({
    queryKey: ['dashboard', 'recent-results', limit],
    queryFn: async () => {
      const { data } = await apiClient.get<RunsListResponse>('/email-agent/runs', {
        params: {
          needs_human: false,
          limit,
          offset: 0,
        },
      });

      // Transform to RecentResult format
      const results: RecentResult[] = data.items.map((item) => ({
        id: item.run_id,
        type: 'email' as const,
        title: item.email_subject || '(No Subject)',
        subtitle: item.email_sender || 'Unknown',
        timestamp: item.created_at,
        confidence: item.confidence || undefined,
        category: item.category || undefined,
        status: item.status,
      }));

      return results;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
};

// ============================================================================
// Review Queue Queries
// ============================================================================

export const useReviewQueue = (filters?: ReviewQueueFilters) => {
  return useQuery({
    queryKey: ['review-queue', 'list', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<ReviewQueueListResponse>('/review-queue', {
        params: filters,
      });
      return data;
    },
    refetchInterval: 15000, // Refresh every 15s
  });
};

export const useReviewQueueItem = (itemId: number) => {
  return useQuery({
    queryKey: ['review-queue', 'item', itemId],
    queryFn: async () => {
      const { data } = await apiClient.get<ReviewQueueItem>(`/review-queue/${itemId}`);
      return data;
    },
    enabled: !!itemId,
  });
};

export const useReviewQueueStats = (accountId?: string) => {
  return useQuery({
    queryKey: ['review-queue', 'stats', accountId],
    queryFn: async () => {
      const { data } = await apiClient.get<ReviewQueueStats>('/review-queue/stats', {
        params: accountId ? { account_id: accountId } : {},
      });
      return data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
};

// ============================================================================
// Review Queue Mutations
// ============================================================================

export const useApproveReviewItem = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      userFeedback,
      applyAction = false,
    }: {
      itemId: number;
      userFeedback?: string;
      applyAction?: boolean;
    }) => {
      const { data } = await apiClient.post<ActionResponse>(
        `/review-queue/${itemId}/approve`,
        {
          user_feedback: userFeedback,
          apply_action: applyAction,
        }
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate all review queue related queries
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

export const useRejectReviewItem = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      correctedCategory,
      userFeedback,
      applyAction = false,
    }: {
      itemId: number;
      correctedCategory?: string;
      userFeedback?: string;
      applyAction?: boolean;
    }) => {
      const { data } = await apiClient.post<ActionResponse>(
        `/review-queue/${itemId}/reject`,
        {
          corrected_category: correctedCategory,
          user_feedback: userFeedback,
          apply_action: applyAction,
        }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

export const useModifyReviewItem = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      correctedCategory,
      userFeedback,
      applyAction = true,
    }: {
      itemId: number;
      correctedCategory: string;
      userFeedback?: string;
      applyAction?: boolean;
    }) => {
      const { data } = await apiClient.post<ActionResponse>(
        `/review-queue/${itemId}/modify`,
        {
          corrected_category: correctedCategory,
          user_feedback: userFeedback,
          apply_action: applyAction,
        }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

export const useDeleteReviewItem = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (itemId: number) => {
      const { data} = await apiClient.delete(`/review-queue/${itemId}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
    },
  });
};

// ============================================================================
// Attachment Queries
// ============================================================================

export const useAttachments = (filters?: AttachmentFilters) => {
  return useQuery({
    queryKey: ['attachments', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<AttachmentListResponse>('/attachments', {
        params: filters,
      });
      return data;
    },
    enabled: !!(filters?.email_id || filters?.account_id),
  });
};

export const useAttachment = (attachmentId: string) => {
  return useQuery({
    queryKey: ['attachments', attachmentId],
    queryFn: async () => {
      const { data } = await apiClient.get<AttachmentMetadata>(`/attachments/${attachmentId}`);
      return data;
    },
    enabled: !!attachmentId,
  });
};

// Download attachment (triggers browser download)
export const downloadAttachment = async (attachmentId: string, filename: string) => {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/attachments/${attachmentId}/download`);

  if (!response.ok) {
    throw new Error('Download failed');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

// ============================================================================
// Thread Queries
// ============================================================================

export const useThreadSummary = (filters: ThreadSummaryFilters) => {
  return useQuery({
    queryKey: ['threads', filters.thread_id, 'summary', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<ThreadSummary>(
        `/threads/${filters.thread_id}/summary`,
        { params: { account_id: filters.account_id, force_regenerate: filters.force_regenerate } }
      );
      return data;
    },
    enabled: !!(filters.thread_id && filters.account_id),
  });
};

export const useThreadEmails = (threadId: string, accountId?: string) => {
  return useQuery({
    queryKey: ['threads', threadId, 'emails', accountId],
    queryFn: async () => {
      const { data } = await apiClient.get<ThreadEmailsResponse>(
        `/threads/${threadId}/emails`,
        { params: { account_id: accountId } }
      );
      return data;
    },
    enabled: !!threadId,
  });
};
