'use client';

import { formatDistanceToNow } from 'date-fns';
import { Mail, Paperclip, MessageCircle } from 'lucide-react';
import type { EmailListItem as EmailListItemType } from '@/lib/api/queries';

interface EmailListItemProps {
  email: EmailListItemType;
  isSelected: boolean;
  onClick: () => void;
}

export function EmailListItem({ email, isSelected, onClick }: EmailListItemProps) {
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
      case 'unwichtig':
        return 'bg-gray-100 text-gray-600 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getCategoryLabel = (category: string | null) => {
    if (!category) return 'Unknown';
    return category.charAt(0).toUpperCase() + category.slice(1);
  };

  return (
    <div
      onClick={onClick}
      className={`
        p-4 border-b border-gray-200 cursor-pointer transition-colors
        ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'hover:bg-gray-50'}
      `}
    >
      <div className="flex items-start justify-between gap-4">
        {/* Left: Email Info */}
        <div className="flex-1 min-w-0">
          {/* Sender */}
          <div className="flex items-center gap-2 mb-1">
            <Mail className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span className="text-sm font-medium text-gray-900 truncate">
              {email.sender || 'Unknown Sender'}
            </span>
          </div>

          {/* Subject */}
          <div className="text-sm font-semibold text-gray-800 mb-2 line-clamp-1">
            {email.subject || '(No Subject)'}
          </div>

          {/* Metadata Row */}
          <div className="flex items-center gap-3 text-xs text-gray-500">
            {/* Account */}
            <span className="font-medium">{email.account_id}</span>

            {/* Category Badge */}
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium border ${getCategoryColor(
                email.category
              )}`}
            >
              {getCategoryLabel(email.category)}
            </span>

            {/* Confidence */}
            {email.confidence !== null && (
              <span>
                {Math.round(email.confidence * 100)}% confidence
              </span>
            )}

            {/* Attachments */}
            {email.has_attachments && (
              <div className="flex items-center gap-1">
                <Paperclip className="h-3 w-3" />
                <span>Attachments</span>
              </div>
            )}

            {/* Thread */}
            {email.thread_id && (
              <div className="flex items-center gap-1">
                <MessageCircle className="h-3 w-3" />
                <span>Thread</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Timestamp */}
        <div className="flex-shrink-0 text-xs text-gray-500">
          {email.received_at
            ? formatDistanceToNow(new Date(email.received_at), {
                addSuffix: true,
              })
            : 'Unknown'}
        </div>
      </div>
    </div>
  );
}
