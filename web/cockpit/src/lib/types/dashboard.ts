export interface TasksStats {
  pending: number;
  in_progress: number;
  completed_today: number;
  overdue: number;
}

export interface DecisionsStats {
  pending: number;
  decided_today: number;
}

export interface QuestionsStats {
  pending: number;
  answered_today: number;
}

export interface EmailsStats {
  processed_today: number;
  by_category: Record<string, number>;
  high_confidence: number;
  medium_confidence: number;
  low_confidence: number;
}

export interface AccountInfo {
  account_id: string;
  email_address: string;
  active: boolean;
}

export interface DashboardOverview {
  tasks: TasksStats;
  decisions: DecisionsStats;
  questions: QuestionsStats;
  emails: EmailsStats;
  accounts: AccountInfo[];
  needs_human_count: number;
}

export interface TopSender {
  sender: string;
  count: number;
}

export interface TodaySummary {
  date: string;
  emails_processed: number;
  tasks_created: number;
  tasks_completed: number;
  decisions_made: number;
  questions_answered: number;
  top_senders: TopSender[];
}
