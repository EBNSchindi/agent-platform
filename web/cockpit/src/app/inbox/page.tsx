'use client';

import { useState } from 'react';
import { useEmails } from '@/lib/api/queries';
import { AccountSelector } from '@/components/inbox/AccountSelector';
import { EmailListItem } from '@/components/inbox/EmailListItem';
import { EmailDetailView } from '@/components/inbox/EmailDetailView';
import { Loader2, ChevronLeft, ChevronRight, Inbox as InboxIcon } from 'lucide-react';

export default function InboxPage() {
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  // Fetch emails
  const { data, isLoading, error } = useEmails({
    account_id: selectedAccountId || undefined,
    limit: pageSize,
    offset: currentPage * pageSize,
  });

  const emails = data?.emails || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  const handleAccountChange = (accountId: string | null) => {
    setSelectedAccountId(accountId);
    setCurrentPage(0); // Reset to first page
    setSelectedEmailId(null); // Clear selected email
  };

  const handleEmailSelect = (emailId: string) => {
    setSelectedEmailId(emailId);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages - 1) {
      setCurrentPage(currentPage + 1);
      setSelectedEmailId(null);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1);
      setSelectedEmailId(null);
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(0); // Reset to first page
    setSelectedEmailId(null);
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <InboxIcon className="h-6 w-6 text-gray-700" />
            <h1 className="text-2xl font-bold text-gray-900">Inbox</h1>
          </div>

          {/* Page Size Selector */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-600">Show:</span>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="px-3 py-1.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
            <span className="text-gray-600">emails</span>
          </div>
        </div>

        {/* Account Selector */}
        <AccountSelector
          selectedAccountId={selectedAccountId}
          onAccountChange={handleAccountChange}
        />
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Email List */}
        <div className="w-1/2 border-r border-gray-200 flex flex-col bg-white">
          {/* Email Count & Pagination */}
          <div className="p-3 border-b border-gray-200 flex items-center justify-between bg-gray-50">
            <div className="text-sm text-gray-700">
              {total > 0 ? (
                <>
                  Showing {currentPage * pageSize + 1}-
                  {Math.min((currentPage + 1) * pageSize, total)} of {total} emails
                </>
              ) : (
                'No emails'
              )}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrevPage}
                  disabled={currentPage === 0}
                  className="p-1.5 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>

                <span className="text-xs text-gray-600">
                  Page {currentPage + 1} of {totalPages}
                </span>

                <button
                  onClick={handleNextPage}
                  disabled={currentPage >= totalPages - 1}
                  className="p-1.5 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>

          {/* Email List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
                  <p className="text-gray-600">Loading emails...</p>
                </div>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center text-red-600">
                  <p>Failed to load emails</p>
                  <p className="text-sm mt-1">Please try again later</p>
                </div>
              </div>
            ) : emails.length === 0 ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center text-gray-500">
                  <InboxIcon className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                  <p>No emails to display</p>
                  {selectedAccountId && (
                    <p className="text-sm mt-1">
                      Try selecting a different account
                    </p>
                  )}
                </div>
              </div>
            ) : (
              emails.map((email) => (
                <EmailListItem
                  key={email.id || email.email_id}
                  email={email}
                  isSelected={selectedEmailId === email.email_id}
                  onClick={() => handleEmailSelect(email.email_id)}
                />
              ))
            )}
          </div>
        </div>

        {/* Right: Email Detail */}
        <div className="w-1/2 bg-white">
          {selectedEmailId ? (
            <EmailDetailView
              emailId={selectedEmailId}
              onClose={() => setSelectedEmailId(null)}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              <div className="text-center">
                <InboxIcon className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg">Select an email to read</p>
                <p className="text-sm mt-1">
                  Click on an email from the list to view its contents
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
