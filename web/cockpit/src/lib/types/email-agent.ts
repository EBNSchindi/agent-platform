export interface EmailAgentStatus {
  active: boolean;
  emails_processed_today: number;
  pending_runs: number;
  last_run: string | null;
}

export interface RunListItem {
  run_id: string;
  email_id: string;
  email_subject: string | null;
  email_sender: string | null;
  email_received_at: string | null;
  category: string | null;
  confidence: number | null;
  needs_human: boolean;
  status: string;
  created_at: string;
}

export interface RunDetail {
  run_id: string;
  email_id: string;
  email_subject: string | null;
  email_sender: string | null;
  email_received_at: string | null;
  category: string | null;
  confidence: number | null;
  importance_score: number | null;
  draft_reply: string | null;
  needs_human: boolean;
  status: string;
  tasks: Task[];
  decisions: Decision[];
  questions: Question[];
  created_at: string;
}

export interface Task {
  task_id: string;
  description: string;
  priority: string;
  status: string;
  deadline: string | null;
  requires_action_from_me: boolean;
}

export interface Decision {
  decision_id: string;
  question: string;
  options: string[];
  recommendation: string | null;
  urgency: string;
  status: string;
}

export interface Question {
  question_id: string;
  question: string;
  question_type: string;
  urgency: string;
  status: string;
  answer: string | null;
}

export interface RunsListResponse {
  items: RunListItem[];
  total: number;
  limit: number;
  offset: number;
}
