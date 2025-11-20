import { MessageSquare, HelpCircle, CheckCircle2, AlertCircle } from 'lucide-react';
import type { Question } from '@/lib/types/email-agent';

interface QuestionsListProps {
  questions: Question[];
}

export function QuestionsList({ questions }: QuestionsListProps) {
  const getTypeColor = (questionType: string): string => {
    const colorMap: { [key: string]: string } = {
      yes_no: 'bg-green-100 text-green-800 border-green-300',
      information: 'bg-blue-100 text-blue-800 border-blue-300',
      clarification: 'bg-purple-100 text-purple-800 border-purple-300',
      decision: 'bg-orange-100 text-orange-800 border-orange-300',
      opinion: 'bg-pink-100 text-pink-800 border-pink-300',
    };
    return colorMap[questionType.toLowerCase()] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

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
    return status.toLowerCase() === 'answered' ? (
      <CheckCircle2 className="w-5 h-5 text-green-600" />
    ) : (
      <HelpCircle className="w-5 h-5 text-blue-600" />
    );
  };

  const formatQuestionType = (type: string): string => {
    const typeMap: { [key: string]: string } = {
      yes_no: 'Ja/Nein',
      information: 'Information',
      clarification: 'Klarstellung',
      decision: 'Entscheidung',
      opinion: 'Meinung',
    };
    return typeMap[type.toLowerCase()] || type;
  };

  if (questions.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Questions</h2>
        <div className="text-center py-8 text-gray-500">
          <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>Keine Fragen aus dieser Email extrahiert</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          Questions ({questions.length})
        </h2>
      </div>

      <div className="p-6 space-y-4">
        {questions.map((question, index) => (
          <div
            key={question.question_id || index}
            className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">{getStatusIcon(question.status)}</div>

              <div className="flex-1 space-y-3">
                {/* Question Text */}
                <p className="text-gray-900 font-medium">{question.question}</p>

                {/* Answer (if provided) */}
                {question.answer && (
                  <div className="bg-green-50 border border-green-200 rounded p-3">
                    <p className="text-sm text-green-900">
                      <span className="font-medium">Antwort:</span> {question.answer}
                    </p>
                  </div>
                )}

                {/* Metadata Row */}
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  {/* Question Type */}
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${getTypeColor(question.question_type)}`}>
                    {formatQuestionType(question.question_type)}
                  </span>

                  {/* Urgency */}
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${getUrgencyColor(question.urgency)}`}>
                    {question.urgency.toUpperCase()}
                  </span>

                  {/* Response Required */}
                  {question.requires_response && (
                    <div className="flex items-center gap-1 text-orange-600">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-xs font-medium">Response required</span>
                    </div>
                  )}

                  {/* Status */}
                  <span className="text-xs text-gray-500">
                    Status: {question.status}
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
