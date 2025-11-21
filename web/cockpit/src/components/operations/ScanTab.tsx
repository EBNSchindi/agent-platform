'use client';

import { useState } from 'react';
import { useAccounts } from '@/lib/api/queries';
import { AlertCircle, Loader2, PlayCircle, CheckCircle, Database } from 'lucide-react';

interface ScanResult {
  account_id: string;
  emails_scanned: number;
  emails_classified: number;
  sender_preferences_created: number;
  tasks_extracted: number;
  decisions_extracted: number;
  questions_extracted: number;
  scan_duration_seconds: number;
}

export function ScanTab() {
  const { data: accountsData, isLoading: accountsLoading } = useAccounts();
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [daysBack, setDaysBack] = useState<number>(30);
  const [maxEmails, setMaxEmails] = useState<number>(500);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const accounts = accountsData?.accounts || [];

  const handleStartScan = async () => {
    if (!selectedAccount) {
      setError('Please select an account');
      return;
    }

    setIsScanning(true);
    setError(null);
    setScanResult(null);

    try {
      const response = await fetch(`/api/history-scan/${selectedAccount}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          days_back: daysBack,
          max_emails: maxEmails,
        }),
      });

      if (!response.ok) {
        throw new Error(`Scan failed: ${response.statusText}`);
      }

      const result = await response.json();
      setScanResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setIsScanning(false);
    }
  };

  if (accountsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        <span className="ml-3 text-gray-600">Loading accounts...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Database className="w-5 h-5" />
          Mailbox History Scan
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Analyze historical emails to initialize sender preferences and extract tasks/decisions/questions
        </p>
      </div>

      {/* Scan Configuration */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="font-medium text-gray-900">Scan Configuration</h3>

        {/* Account Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Email Account
          </label>
          <select
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
            disabled={isScanning}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="">Select an account...</option>
            {accounts.map((account) => (
              <option key={account.account_id} value={account.account_id}>
                {account.account_id} ({account.email})
              </option>
            ))}
          </select>
        </div>

        {/* Days Back */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Days Back
          </label>
          <input
            type="number"
            min="1"
            max="365"
            value={daysBack}
            onChange={(e) => setDaysBack(parseInt(e.target.value))}
            disabled={isScanning}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-gray-500 mt-1">
            How many days of email history to analyze (1-365)
          </p>
        </div>

        {/* Max Emails */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Emails
          </label>
          <input
            type="number"
            min="10"
            max="10000"
            step="50"
            value={maxEmails}
            onChange={(e) => setMaxEmails(parseInt(e.target.value))}
            disabled={isScanning}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-gray-500 mt-1">
            Maximum number of emails to process (10-10000)
          </p>
        </div>

        {/* Start Button */}
        <button
          onClick={handleStartScan}
          disabled={isScanning || !selectedAccount}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {isScanning ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Scanning...
            </>
          ) : (
            <>
              <PlayCircle className="w-5 h-5" />
              Start History Scan
            </>
          )}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <div>
            <p className="font-medium text-red-900">Scan Failed</p>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Scan Result */}
      {scanResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-6 h-6 text-green-600" />
            <h3 className="font-semibold text-green-900 text-lg">Scan Completed Successfully</h3>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg p-4">
              <p className="text-sm text-gray-600">Emails Scanned</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {scanResult.emails_scanned}
              </p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <p className="text-sm text-gray-600">Classified</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {scanResult.emails_classified}
              </p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <p className="text-sm text-gray-600">Sender Preferences</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {scanResult.sender_preferences_created}
              </p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <p className="text-sm text-gray-600">Duration</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {scanResult.scan_duration_seconds.toFixed(1)}s
              </p>
            </div>
          </div>

          <div className="bg-white rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-3">Extracted Items</h4>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-3xl font-bold text-blue-600">
                  {scanResult.tasks_extracted}
                </p>
                <p className="text-sm text-gray-600 mt-1">Tasks</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-purple-600">
                  {scanResult.decisions_extracted}
                </p>
                <p className="text-sm text-gray-600 mt-1">Decisions</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-orange-600">
                  {scanResult.questions_extracted}
                </p>
                <p className="text-sm text-gray-600 mt-1">Questions</p>
              </div>
            </div>
          </div>

          <p className="text-sm text-gray-600">
            Account <span className="font-mono font-medium">{scanResult.account_id}</span> history scan completed.
            The system has learned from your email patterns and initialized sender preferences.
          </p>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">What does History Scan do?</h4>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>Analyzes past emails to learn sender importance patterns</li>
          <li>Extracts tasks, decisions, and questions from historical emails</li>
          <li>Initializes the learning system with your email behavior</li>
          <li>Creates sender preferences using EMA (Exponential Moving Average)</li>
          <li>Useful for initial setup or when adding a new account</li>
        </ul>
      </div>
    </div>
  );
}
