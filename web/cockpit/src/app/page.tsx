'use client';

import {
  QuickStats,
  ActiveTasksColumn,
  NeedsHumanColumn,
  RecentResultsColumn,
  ActivityFeed
} from '@/components/dashboard/DashboardComponents';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Cockpit</h1>
        <p className="text-gray-600 mt-1">
          Your Digital Twin Email Platform control center
        </p>
      </div>

      {/* Quick Stats Row */}
      <QuickStats />

      {/* 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Active Tasks */}
        <div className="h-[600px]">
          <ActiveTasksColumn />
        </div>

        {/* Middle: Needs Human */}
        <div className="h-[600px]">
          <NeedsHumanColumn />
        </div>

        {/* Right: Recent Results */}
        <div className="h-[600px]">
          <RecentResultsColumn />
        </div>
      </div>

      {/* Activity Feed (Full Width) */}
      <ActivityFeed />
    </div>
  );
}
