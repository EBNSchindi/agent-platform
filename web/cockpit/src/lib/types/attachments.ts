/**
 * TypeScript types for Attachment API
 * Matches backend Pydantic models from agent_platform/attachments/models.py
 */

export interface AttachmentMetadata {
  id: number;
  attachment_id: string;
  email_id: string;
  account_id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  stored_path: string | null;
  storage_status: 'pending' | 'downloaded' | 'failed' | 'skipped_too_large';
  downloaded_at: string | null;
  file_hash: string | null;
  extracted_text: string | null;
  extraction_status: string | null;
  created_at: string;
}

export interface AttachmentListResponse {
  total: number;
  items: AttachmentMetadata[];
  account_id?: string | null;
  email_id?: string | null;
}

export interface AttachmentFilters {
  email_id?: string;
  account_id?: string;
  limit?: number;
  offset?: number;
}

// Helper type for file size formatting
export type FileSizeUnit = 'B' | 'KB' | 'MB' | 'GB';

// Helper function to format file size
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)}GB`;
}

// Helper to get icon for file type
export function getFileTypeIcon(mimeType: string): string {
  if (mimeType.startsWith('image/')) return '🖼️';
  if (mimeType.startsWith('video/')) return '🎥';
  if (mimeType.startsWith('audio/')) return '🎵';
  if (mimeType.includes('pdf')) return '📄';
  if (mimeType.includes('word') || mimeType.includes('document')) return '📝';
  if (mimeType.includes('sheet') || mimeType.includes('excel')) return '📊';
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📽️';
  if (mimeType.includes('zip') || mimeType.includes('archive')) return '📦';
  return '📎';
}

// Helper to get status badge color
export function getStatusColor(status: AttachmentMetadata['storage_status']): string {
  const colorMap = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    downloaded: 'bg-green-100 text-green-800 border-green-300',
    failed: 'bg-red-100 text-red-800 border-red-300',
    skipped_too_large: 'bg-gray-100 text-gray-800 border-gray-300',
  };
  return colorMap[status] || 'bg-gray-100 text-gray-800 border-gray-300';
}

// Helper to get status label
export function getStatusLabel(status: AttachmentMetadata['storage_status']): string {
  const labelMap = {
    pending: 'Pending',
    downloaded: 'Downloaded',
    failed: 'Failed',
    skipped_too_large: 'Too Large',
  };
  return labelMap[status] || status;
}
