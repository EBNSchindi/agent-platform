import { Download, FileText, Loader2 } from 'lucide-react';
import { useAttachments, downloadAttachment } from '@/lib/api/queries';
import { formatFileSize, getFileTypeIcon, getStatusColor, getStatusLabel } from '@/lib/types/attachments';
import type { AttachmentFilters } from '@/lib/types/attachments';

interface AttachmentsListProps {
  emailId?: string;
  accountId?: string;
}

export function AttachmentsList({ emailId, accountId }: AttachmentsListProps) {
  const filters: AttachmentFilters = { email_id: emailId, account_id: accountId, limit: 50 };
  const { data, isLoading, error } = useAttachments(filters);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-800">Failed to load attachments</p>
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6 text-center">
        <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
        <p className="text-gray-500">No attachments</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">
          Attachments ({data.total})
        </h3>
      </div>

      <div className="p-4 space-y-2">
        {data.items.map((attachment) => (
          <div
            key={attachment.attachment_id}
            className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            {/* Left: Icon + Name + Size */}
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <span className="text-2xl">{getFileTypeIcon(attachment.mime_type)}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {attachment.original_filename}
                </p>
                <p className="text-xs text-gray-500">
                  {formatFileSize(attachment.file_size_bytes)} • {attachment.mime_type}
                </p>
              </div>
            </div>

            {/* Right: Status + Download Button */}
            <div className="flex items-center gap-3">
              <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(attachment.storage_status)}`}>
                {getStatusLabel(attachment.storage_status)}
              </span>

              {attachment.storage_status === 'downloaded' && (
                <button
                  onClick={() => downloadAttachment(attachment.attachment_id, attachment.original_filename)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
                  title="Download"
                >
                  <Download className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
