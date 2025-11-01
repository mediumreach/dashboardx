import { BarChart3, TrendingUp, Users, FileText, Bot, Activity } from 'lucide-react';

export function AnalyticsPage() {

  const metrics = [
    { name: 'Total Documents', value: '0', icon: FileText, color: 'blue' },
    { name: 'Active Agents', value: '0', icon: Bot, color: 'purple' },
    { name: 'Total Queries', value: '0', icon: Activity, color: 'green' },
    { name: 'Users', value: '0', icon: Users, color: 'orange' },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900" data-testid="text-page-title">Analytics</h1>
        <p className="text-gray-600 mt-1">Monitor your platform usage and performance</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.name}
              className="bg-white rounded-lg border border-gray-200 p-6"
              data-testid={`card-metric-${metric.name.toLowerCase().replace(' ', '-')}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">{metric.name}</span>
                <Icon className={`w-5 h-5 text-${metric.color}-600`} />
              </div>
              <p className="text-3xl font-bold text-gray-900">{metric.value}</p>
              <div className="flex items-center gap-1 mt-2 text-sm text-green-600">
                <TrendingUp className="w-4 h-4" />
                <span>--</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Placeholder */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Query Volume</h3>
          <div className="h-64 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <BarChart3 className="w-12 h-12 mx-auto mb-2" />
              <p>No data available yet</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Agent Performance</h3>
          <div className="h-64 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Activity className="w-12 h-12 mx-auto mb-2" />
              <p>No data available yet</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
