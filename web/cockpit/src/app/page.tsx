export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Cockpit</h1>

      <div className="grid grid-cols-3 gap-6">
        {/* Active Tasks Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Aktive Tasks</h2>
          <div className="text-3xl font-bold text-blue-600">15</div>
          <p className="text-sm text-gray-600 mt-2">3 in Bearbeitung</p>
        </div>

        {/* Needs Human Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Needs Human</h2>
          <div className="text-3xl font-bold text-orange-600">8</div>
          <p className="text-sm text-gray-600 mt-2">Warten auf dich</p>
        </div>

        {/* Recent Results Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Letzte Ergebnisse</h2>
          <div className="text-3xl font-bold text-green-600">42</div>
          <p className="text-sm text-gray-600 mt-2">Heute verarbeitet</p>
        </div>
      </div>

      {/* Activity Feed */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Activity Feed</h2>
        <div className="space-y-3">
          <div className="flex items-start gap-3 text-sm">
            <span className="text-gray-500">08:12</span>
            <span className="text-gray-700">Email-Agent: 5 neue Mails kategorisiert</span>
          </div>
          <div className="flex items-start gap-3 text-sm">
            <span className="text-gray-500">08:25</span>
            <span className="text-gray-700">Journal generiert für gmail_1</span>
          </div>
          <div className="flex items-start gap-3 text-sm">
            <span className="text-gray-500">09:00</span>
            <span className="text-gray-700">3 Tasks als erledigt markiert</span>
          </div>
        </div>
      </div>
    </div>
  );
}
