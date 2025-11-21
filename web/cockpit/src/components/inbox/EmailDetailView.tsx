'use client';

import { useEmailDetail } from '@/lib/api/queries';
import { formatDistanceToNow } from 'date-fns';
import {
  Loader2,
  Mail,
  Calendar,
  Paperclip,
  CheckSquare,
  HelpCircle,
  AlertCircle,
  X,
} from 'lucide-react';

interface EmailDetailViewProps {
  emailId: string;
  onClose: () => void;
}

export function EmailDetailView({ emailId, onClose }: EmailDetailViewProps) {
  const { data: email, isLoading, error } = useEmailDetail(emailId);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-gray-600">Loading email...</p>
        </div>
      </div>
    );
  }

  if (error || !email) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="text-center text-red-600">
          <p>Failed to load email</p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const getCategoryColor = (category: string | null) => {
    switch (category) {
      case 'wichtig':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'action_required':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'nice_to_know':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'newsletter':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Subject */}
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {email.subject || '(No Subject)'}
            </h2>

            {/* Sender & Date */}
            <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                <span>{email.sender || 'Unknown Sender'}</span>
              </div>

              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                <span>
                  {email.received_at
                    ? formatDistanceToNow(new Date(email.received_at), {
                        addSuffix: true,
                      })
                    : 'Unknown date'}
                </span>
              </div>
            </div>

            {/* Metadata */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 font-medium">
                {email.account_id}
              </span>

              <span
                className={`px-2 py-1 rounded text-xs font-medium border ${getCategoryColor(
                  email.category
                )}`}
              >
                {email.category}
              </span>

              {email.confidence !== null && (
                <span className="text-xs text-gray-500">
                  {Math.round(email.confidence * 100)}% confidence
                </span>
              )}

              {email.has_attachments && (
                <div className="flex items-center gap-1 text-xs text-gray-600">
                  <Paperclip className="h-3 w-3" />
                  <span>Has attachments</span>
                </div>
              )}
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Email Body */}
        <div className="mb-8">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Email Content</h3>

          {email.body_html ? (
            // Render HTML body (sanitized)
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: email.body_html }}
            />
          ) : email.body_text ? (
            // Render plain text body
            <div className="whitespace-pre-wrap text-gray-800 font-mono text-sm">
              {email.body_text}
            </div>
          ) : (
            <p className="text-gray-500 italic">No email body available</p>
          )}
        </div>

        {/* Extracted Tasks */}
        {email.tasks && email.tasks.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <CheckSquare className="h-5 w-5 text-green-600" />
              <h3 className="text-sm font-semibold text-gray-700">
                Extracted Tasks ({email.tasks.length})
              </h3>
            </div>

            <div className="space-y-2">
              {email.tasks.map((task: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-green-50 border border-green-200 rounded-lg"
                >
                  <div className="font-medium text-gray-900">{task.description}</div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                    {task.deadline && (
                      <span>Deadline: {task.deadline}</span>
                    )}
                    {task.priority && (
                      <span className="font-medium">Priority: {task.priority}</span>
                    )}
                    {task.status && (
                      <span>Status: {task.status}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Extracted Decisions */}
        {email.decisions && email.decisions.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="h-5 w-5 text-orange-600" />
              <h3 className="text-sm font-semibold text-gray-700">
                Extracted Decisions ({email.decisions.length})
              </h3>
            </div>

            <div className="space-y-2">
              {email.decisions.map((decision: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-orange-50 border border-orange-200 rounded-lg"
                >
                  <div className="font-medium text-gray-900">{decision.question}</div>
                  {decision.options && (
                    <div className="mt-2 text-sm text-gray-700">
                      Options: {decision.options.join(', ')}
                    </div>
                  )}
                  {decision.recommendation && (
                    <div className="mt-1 text-xs text-gray-600">
                      Recommended: {decision.recommendation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Extracted Questions */}
        {email.questions && email.questions.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <HelpCircle className="h-5 w-5 text-blue-600" />
              <h3 className="text-sm font-semibold text-gray-700">
                Extracted Questions ({email.questions.length})
              </h3>
            </div>

            <div className="space-y-2">
              {email.questions.map((question: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-blue-50 border border-blue-200 rounded-lg"
                >
                  <div className="font-medium text-gray-900">{question.question}</div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                    {question.question_type && (
                      <span>Type: {question.question_type}</span>
                    )}
                    {question.urgency && (
                      <span>Urgency: {question.urgency}</span>
                    )}
                    {question.status && (
                      <span>Status: {question.status}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
