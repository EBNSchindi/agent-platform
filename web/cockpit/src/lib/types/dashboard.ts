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

// Activity Feed
export interface ActivityItem {
  activity_id: string;
  timestamp: string;
  event_type: string;
  description: string;
  icon_type: 'email' | 'task' | 'decision' | 'question' | 'user' | 'system';
  account_id: string | null;
  email_id: string | null;
  metadata: Record<string, any>;
}

export interface ActivityFeedResponse {
  items: ActivityItem[];
  total: number;
  limit: number;
  offset: number;
}

// Dashboard specific item types
export interface TaskItem {
  task_id: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'waiting';
  deadline: string | null;
  requires_action_from_me: boolean;
  email_subject: string | null;
  email_sender: string | null;
  created_at: string;
}

export interface DecisionItem {
  decision_id: string;
  question: string;
  options: string[];
  recommendation: string | null;
  urgency: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'decided' | 'cancelled';
  requires_my_input: boolean;
  email_subject: string | null;
  email_sender: string | null;
  created_at: string;
}

export interface QuestionItem {
  question_id: string;
  question: string;
  question_type: string;
  urgency: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'answered' | 'cancelled';
  requires_response: boolean;
  answer: string | null;
  email_subject: string | null;
  email_sender: string | null;
  created_at: string;
}

export interface RecentResult {
  id: string;
  type: 'email' | 'task' | 'decision' | 'question';
  title: string;
  subtitle: string;
  timestamp: string;
  confidence?: number;
  category?: string;
  status: string;
}
