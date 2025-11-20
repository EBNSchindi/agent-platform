'use client';

import { useState } from 'react';
import { useReviewQueue } from '@/lib/api/queries';
import {
  ReviewQueueCard,
  ReviewQueueStats,
} from '@/components/review-queue/ReviewQueueComponents';
import {
  Filter,
  RefreshCw,
  ListFilter,
  Loader2,
} from 'lucide-react';
import type { ReviewQueueFilters } from '@/lib/types/review-queue';

export default function ReviewQueuePage() {
  // Filters
  const [filters, setFilters] = useState<ReviewQueueFilters>({
    status: 'pending',
    limit: 20,
    offset: 0,
  });

  // Fetch data
  const { data, isLoading, refetch, isFetching } = useReviewQueue(filters);

  // Handle filter changes
  const handleStatusChange = (status: string) => {
    setFilters({ ...filters, status: status as any, offset: 0 });
  };

  const handleRefresh = () => {
    refetch();
  };

  const handleLoadMore = () => {
    if (data && data.items.length < data.total) {
      setFilters({ ...filters, offset: (filters.offset || 0) + (filters.limit || 20) });
    }
  };

  // Status tabs
  const statusTabs = [
    { value: 'pending', label: 'Pending', color: 'orange' },
    { value: 'approved', label: 'Approved', color: 'green' },
    { value: 'rejected', label: 'Rejected', color: 'red' },
    { value: 'modified', label: 'Modified', color: 'blue' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Review Queue</h1>
          <p className="text-sm text-gray-600 mt-1">
            Review and approve email classifications
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isFetching}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stats and Filters Row */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Stats Sidebar */}
        <div className="lg:col-span-1">
          <ReviewQueueStats />
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-4">
          {/* Status Tabs */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 mb-3">
              <ListFilter className="w-5 h-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Filter by Status:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {statusTabs.map((tab) => {
                const isActive = filters.status === tab.value;
                const colorClasses = {
                  orange: isActive
                    ? 'bg-orange-600 text-white border-orange-600'
                    : 'bg-white text-orange-600 border-orange-200 hover:bg-orange-50',
                  green: isActive
                    ? 'bg-green-600 text-white border-green-600'
                    : 'bg-white text-green-600 border-green-200 hover:bg-green-50',
                  red: isActive
                    ? 'bg-red-600 text-white border-red-600'
                    : 'bg-white text-red-600 border-red-200 hover:bg-red-50',
                  blue: isActive
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-blue-600 border-blue-200 hover:bg-blue-50',
                }[tab.color];

                return (
                  <button
                    key={tab.value}
                    onClick={() => handleStatusChange(tab.value)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg border transition ${colorClasses}`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Results Info */}
          {data && (
            <div className="flex items-center justify-between text-sm text-gray-600 px-2">
              <span>
                Showing {data.items.length} of {data.total} items
                {filters.status !== 'pending' && (
                  <span className="ml-2">
                    ({data.pending_count} pending)
                  </span>
                )}
              </span>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
                <p className="text-sm text-gray-600">Loading review queue...</p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && data && data.items.length === 0 && (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <ListFilter className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No Items Found
              </h3>
              <p className="text-sm text-gray-600">
                {filters.status === 'pending'
                  ? 'All caught up! No pending reviews at the moment.'
                  : `No ${filters.status} items found.`}
              </p>
            </div>
          )}

          {/* Review Queue Items */}
          {!isLoading && data && data.items.length > 0 && (
            <div className="space-y-4">
              {data.items.map((item) => (
                <ReviewQueueCard
                  key={item.id}
                  item={item}
                  onActionComplete={handleRefresh}
                />
              ))}

              {/* Load More Button */}
              {data.items.length < data.total && (
                <button
                  onClick={handleLoadMore}
                  disabled={isFetching}
                  className="w-full py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {isFetching ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading more...
                    </span>
                  ) : (
                    `Load More (${data.total - data.items.length} remaining)`
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
