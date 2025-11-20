import { Mail, Clock, AlertCircle, CheckCircle } from 'lucide-react';
import { ConfidenceIndicator } from './ConfidenceIndicator';

interface EmailMetadataProps {
  emailSubject: string | null;
  emailSender: string | null;
  emailReceivedAt: string | null;
  category: string | null;
  confidence: number | null;
  importanceScore: number | null;
  needsHuman: boolean;
  status: string;
  createdAt: string;
}

export function EmailMetadata({
  emailSubject,
  emailSender,
  emailReceivedAt,
  category,
  confidence,
  importanceScore,
  needsHuman,
  status,
  createdAt,
}: EmailMetadataProps) {
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('de-DE', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  const getCategoryColor = (cat: string | null): string => {
    if (!cat) return 'bg-gray-100 text-gray-800';

    const colorMap: { [key: string]: string } = {
      wichtig: 'bg-red-100 text-red-800',
      normal: 'bg-blue-100 text-blue-800',
      unwichtig: 'bg-gray-100 text-gray-800',
    };

    return colorMap[cat.toLowerCase()] || 'bg-blue-100 text-blue-800';
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Mail className="w-6 h-6 text-blue-600" />
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-semibold text-gray-900 mb-1">
              {emailSubject || '(Kein Betreff)'}
            </h1>
            <p className="text-sm text-gray-600">
              Von: <span className="font-medium">{emailSender || '(Unbekannt)'}</span>
            </p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {/* Date and Category Row */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Clock className="w-4 h-4" />
            <span>Empfangen: {formatDate(emailReceivedAt)}</span>
          </div>

          {category && (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCategoryColor(category)}`}>
              {category}
            </span>
          )}
        </div>

        {/* Confidence and Importance */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600 mb-2">Confidence</p>
            <ConfidenceIndicator confidence={confidence} size="lg" />
          </div>

          {importanceScore !== null && (
            <div>
              <p className="text-sm text-gray-600 mb-2">Importance Score</p>
              <p className="text-2xl font-bold text-gray-900">
                {importanceScore.toFixed(2)}
              </p>
            </div>
          )}
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <p className="text-sm text-gray-600">Status:</p>
          {needsHuman ? (
            <span className="inline-flex items-center gap-1 text-xs text-orange-700 bg-orange-100 px-2 py-1 rounded">
              <AlertCircle className="w-3 h-3" />
              Needs Review
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-100 px-2 py-1 rounded">
              <CheckCircle className="w-3 h-3" />
              Confident
            </span>
          )}
          <span className="text-xs text-gray-500">({status})</span>
        </div>
      </div>

      {/* Footer with Created Date */}
      <div className="px-6 py-3 bg-gray-50 text-xs text-gray-600">
        Verarbeitet: {formatDate(createdAt)}
      </div>
    </div>
  );
}
