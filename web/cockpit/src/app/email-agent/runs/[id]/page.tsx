'use client';

import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import { useRun } from '@/lib/api/queries';
import { EmailMetadata } from '@/components/email-agent/EmailMetadata';
import { TasksList } from '@/components/email-agent/TasksList';
import { DecisionsList } from '@/components/email-agent/DecisionsList';
import { QuestionsList } from '@/components/email-agent/QuestionsList';
import { HITLActions } from '@/components/email-agent/HITLActions';

export default function RunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const { data: run, isLoading, error } = useRun(runId);

  // Loading State
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-blue-600" />
          <p className="text-gray-600">Loading run details...</p>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    const errorStatus = (error as any)?.response?.status;
    const isNotFound = errorStatus === 404;

    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <AlertCircle className="w-8 h-8 text-red-600 flex-shrink-0" />
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-red-900 mb-2">
                {isNotFound ? 'Run Not Found' : 'Error Loading Run'}
              </h2>
              <p className="text-red-700 mb-4">
                {isNotFound
                  ? `Run with ID "${runId}" was not found in the database.`
                  : 'Failed to load run details. Please try again later.'}
              </p>
              <button
                onClick={() => router.push('/email-agent')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Overview
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // No data (shouldn't happen if no error, but defensive)
  if (!run) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">No run data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Back Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push('/email-agent')}
          className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Zurück
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Run Details</h1>
      </div>

      {/* Email Metadata Card */}
      <EmailMetadata
        emailSubject={run.email_subject}
        emailSender={run.email_sender}
        emailReceivedAt={run.email_received_at}
        category={run.category}
        confidence={run.confidence}
        importanceScore={run.importance_score}
        needsHuman={run.needs_human}
        status={run.status}
        createdAt={run.created_at}
      />

      {/* Main Content: 2-Column Layout (Desktop) / 1-Column (Mobile) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Tasks, Decisions, Questions */}
        <div className="lg:col-span-2 space-y-6">
          <TasksList tasks={run.tasks || []} />
          <DecisionsList decisions={run.decisions || []} />
          <QuestionsList questions={run.questions || []} />
        </div>

        {/* Right Column: HITL Actions (Sticky on Desktop) */}
        <div className="lg:col-span-1">
          <HITLActions
            runId={run.run_id}
            currentCategory={run.category}
            confidence={run.confidence}
            status={run.status}
          />
        </div>
      </div>

      {/* Draft Reply Section (if available) */}
      {run.draft_reply && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Draft Reply</h2>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans">
              {run.draft_reply}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
