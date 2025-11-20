'use client';

import { useEmailAgentStatus, useEmailAgentRuns } from '@/lib/api/queries';
import { Mail, Clock, AlertCircle, CheckCircle } from 'lucide-react';

export default function EmailAgentPage() {
  const { data: status, isLoading: statusLoading } = useEmailAgentStatus();
  const { data: runs, isLoading: runsLoading } = useEmailAgentRuns({ limit: 10 });

  if (statusLoading) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Email-Agent</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
          Test-Run auslösen
        </button>
      </div>

      {/* Status Card */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Status</h2>
              <div className="flex items-center gap-2 mt-2">
                {status?.active ? (
                  <span className="inline-flex items-center gap-1 text-sm text-green-700 bg-green-100 px-3 py-1 rounded-full">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    Aktiv
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-sm text-gray-700 bg-gray-100 px-3 py-1 rounded-full">
                    <span className="w-2 h-2 rounded-full bg-gray-500"></span>
                    Pausiert
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-8">
              <div>
                <p className="text-sm text-gray-600">Heute verarbeitet</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {status?.emails_processed_today || 0}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Warten auf dich</p>
                <p className="text-3xl font-bold text-orange-600 mt-1">
                  {status?.pending_runs || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        {status?.last_run && (
          <div className="px-6 py-3 bg-gray-50 text-sm text-gray-600">
            Letzter Run: {new Date(status.last_run).toLocaleString('de-DE')}
          </div>
        )}
      </div>

      {/* Runs Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Letzte Runs</h2>
        </div>

        {runsLoading ? (
          <div className="p-6 text-center text-gray-600">Loading runs...</div>
        ) : runs && runs.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Zeit
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Betreff
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Absender
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Kategorie
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {runs.items.map((run) => (
                  <tr
                    key={run.run_id}
                    className="hover:bg-gray-50 cursor-pointer transition"
                    onClick={() => window.location.href = `/email-agent/runs/${run.run_id}`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        {new Date(run.created_at).toLocaleTimeString('de-DE')}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-xs truncate">
                        {run.email_subject || '(Kein Betreff)'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {run.email_sender || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {run.category || 'unbekannt'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              (run.confidence || 0) >= 0.9
                                ? 'bg-green-500'
                                : (run.confidence || 0) >= 0.65
                                ? 'bg-yellow-500'
                                : 'bg-red-500'
                            }`}
                            style={{ width: `${(run.confidence || 0) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-gray-600">
                          {((run.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {run.needs_human ? (
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-center text-gray-600">
            <Mail className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>Keine Runs vorhanden</p>
          </div>
        )}
      </div>
    </div>
  );
}
