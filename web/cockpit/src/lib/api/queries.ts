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
