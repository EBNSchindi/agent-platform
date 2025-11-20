import { GitBranch, AlertTriangle, CheckCircle2, User } from 'lucide-react';
import type { Decision } from '@/lib/types/email-agent';

interface DecisionsListProps {
  decisions: Decision[];
}

export function DecisionsList({ decisions }: DecisionsListProps) {
  const getUrgencyColor = (urgency: string): string => {
    const colorMap: { [key: string]: string } = {
      urgent: 'bg-red-100 text-red-800 border-red-300',
      high: 'bg-orange-100 text-orange-800 border-orange-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-gray-100 text-gray-800 border-gray-300',
    };
    return colorMap[urgency.toLowerCase()] || colorMap.medium;
  };

  const getStatusIcon = (status: string) => {
    return status.toLowerCase() === 'decided' ? (
      <CheckCircle2 className="w-5 h-5 text-green-600" />
    ) : (
      <AlertTriangle className="w-5 h-5 text-orange-600" />
    );
  };

  if (decisions.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Decisions Required</h2>
        <div className="text-center py-8 text-gray-500">
          <GitBranch className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>Keine Entscheidungen aus dieser Email extrahiert</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          Decisions Required ({decisions.length})
        </h2>
      </div>

      <div className="p-6 space-y-4">
        {decisions.map((decision, index) => (
          <div
            key={decision.decision_id || index}
            className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">{getStatusIcon(decision.status)}</div>

              <div className="flex-1 space-y-3">
                {/* Question */}
                <p className="text-gray-900 font-medium">{decision.question}</p>

                {/* Options */}
                {decision.options && decision.options.length > 0 && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Optionen:</p>
                    <ul className="space-y-1">
                      {decision.options.map((option, optIndex) => (
                        <li
                          key={optIndex}
                          className="flex items-start gap-2 text-sm text-gray-700"
                        >
                          <span className="text-gray-400">•</span>
                          <span>{option}</span>
                          {decision.recommendation === option && (
                            <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                              Empfohlen
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recommendation (if not shown inline) */}
                {decision.recommendation && !decision.options.includes(decision.recommendation) && (
                  <div className="bg-blue-50 border border-blue-200 rounded p-2">
                    <p className="text-sm text-blue-900">
                      <span className="font-medium">Empfehlung:</span> {decision.recommendation}
                    </p>
                  </div>
                )}

                {/* Metadata Row */}
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  {/* Urgency */}
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${getUrgencyColor(decision.urgency)}`}>
                    {decision.urgency.toUpperCase()}
                  </span>

                  {/* Requires My Input */}
                  {(decision as any).requires_my_input && (
                    <div className="flex items-center gap-1 text-orange-600">
                      <User className="w-4 h-4" />
                      <span className="text-xs font-medium">Requires your input</span>
                    </div>
                  )}

                  {/* Status */}
                  <span className="text-xs text-gray-500">
                    Status: {decision.status}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
