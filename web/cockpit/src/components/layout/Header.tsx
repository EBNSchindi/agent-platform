'use client';

export function Header() {
  return (
    <header className="h-16 bg-white border-b border-gray-200 px-6 flex items-center justify-between">
      {/* Left: Twin Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-sm">
            DT
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Daniel Twin</h2>
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>
              <span className="text-xs text-gray-600">Learning Mode</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Mode Switch & Actions */}
      <div className="flex items-center gap-4">
        {/* Mode Switch (disabled for now) */}
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white text-gray-700 cursor-not-allowed opacity-50"
          disabled
        >
          <option>Work Mode</option>
          <option>Events Mode</option>
          <option>Private Mode</option>
          <option>Learning Mode</option>
        </select>

        {/* Status Indicator */}
        <div className="flex items-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg text-sm">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span>All Systems Operational</span>
        </div>
      </div>
    </header>
  );
}
