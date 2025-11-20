import { useState } from 'react';
import { Play, Loader2 } from 'lucide-react';
import { useStartScan } from '@/lib/api/queries';
import type { ScanConfig } from '@/lib/types/history-scan';

interface StartScanFormProps {
  onScanStarted?: (scanId: string) => void;
}

export function StartScanForm({ onScanStarted }: StartScanFormProps) {
  const [config, setConfig] = useState<ScanConfig>({
    account_id: 'gmail_1',
    batch_size: 50,
    max_results: null,
    query: '',
    skip_already_processed: true,
    process_attachments: true,
    process_threads: true,
  });

  const startScan = useStartScan();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const result = await startScan.mutateAsync(config);
      if (onScanStarted) {
        onScanStarted(result.scan_id);
      }
    } catch (error) {
      console.error('Failed to start scan:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Start History Scan</h2>

      {/* Account ID */}
      <div>
        <label htmlFor="account_id" className="block text-sm font-medium text-gray-700 mb-1">
          Account ID
        </label>
        <input
          type="text"
          id="account_id"
          value={config.account_id}
          onChange={(e) => setConfig({ ...config, account_id: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          required
        />
      </div>

      {/* Gmail Query Filter */}
      <div>
        <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-1">
          Gmail Query Filter (optional)
        </label>
        <input
          type="text"
          id="query"
          value={config.query}
          onChange={(e) => setConfig({ ...config, query: e.target.value })}
          placeholder="e.g., after:2023/01/01 from:example@gmail.com"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-xs text-gray-500">
          Use Gmail search syntax to filter emails. Leave empty to scan all.
        </p>
      </div>

      {/* Batch Size & Max Results */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="batch_size" className="block text-sm font-medium text-gray-700 mb-1">
            Batch Size
          </label>
          <input
            type="number"
            id="batch_size"
            value={config.batch_size}
            onChange={(e) => setConfig({ ...config, batch_size: parseInt(e.target.value) || 50 })}
            min="10"
            max="500"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="mt-1 text-xs text-gray-500">10-500 emails per batch</p>
        </div>

        <div>
          <label htmlFor="max_results" className="block text-sm font-medium text-gray-700 mb-1">
            Max Results (optional)
          </label>
          <input
            type="number"
            id="max_results"
            value={config.max_results ?? ''}
            onChange={(e) =>
              setConfig({ ...config, max_results: e.target.value ? parseInt(e.target.value) : null })
            }
            min="1"
            placeholder="All"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="mt-1 text-xs text-gray-500">Leave empty for all</p>
        </div>
      </div>

      {/* Options Checkboxes */}
      <div className="space-y-2">
        <div className="flex items-center">
          <input
            type="checkbox"
            id="skip_already_processed"
            checked={config.skip_already_processed}
            onChange={(e) => setConfig({ ...config, skip_already_processed: e.target.checked })}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label htmlFor="skip_already_processed" className="ml-2 text-sm text-gray-700">
            Skip already processed emails
          </label>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="process_attachments"
            checked={config.process_attachments}
            onChange={(e) => setConfig({ ...config, process_attachments: e.target.checked })}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label htmlFor="process_attachments" className="ml-2 text-sm text-gray-700">
            Download and process attachments
          </label>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="process_threads"
            checked={config.process_threads}
            onChange={(e) => setConfig({ ...config, process_threads: e.target.checked })}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label htmlFor="process_threads" className="ml-2 text-sm text-gray-700">
            Generate thread summaries
          </label>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={startScan.isPending}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {startScan.isPending ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Starting scan...
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            Start Scan
          </>
        )}
      </button>

      {/* Error Display */}
      {startScan.isError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">
            Failed to start scan. Please check your configuration and try again.
          </p>
        </div>
      )}
    </form>
  );
}
