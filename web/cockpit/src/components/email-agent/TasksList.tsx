import { ListTodo, Calendar, Flag, CheckCircle, Circle, Clock } from 'lucide-react';
import type { Task } from '@/lib/types/email-agent';

interface TasksListProps {
  tasks: Task[];
}

export function TasksList({ tasks }: TasksListProps) {
  const getPriorityColor = (priority: string): string => {
    const colorMap: { [key: string]: string } = {
      urgent: 'bg-red-100 text-red-800 border-red-300',
      high: 'bg-orange-100 text-orange-800 border-orange-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-gray-100 text-gray-800 border-gray-300',
    };
    return colorMap[priority.toLowerCase()] || colorMap.low;
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'in_progress':
        return <Clock className="w-5 h-5 text-blue-600" />;
      default:
        return <Circle className="w-5 h-5 text-gray-400" />;
    }
  };

  const formatDeadline = (deadline: string | null): string => {
    if (!deadline) return 'Keine Deadline';

    try {
      const date = new Date(deadline);
      return date.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return deadline;
    }
  };

  if (tasks.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Extracted Tasks</h2>
        <div className="text-center py-8 text-gray-500">
          <ListTodo className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>Keine Tasks aus dieser Email extrahiert</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          Extracted Tasks ({tasks.length})
        </h2>
      </div>

      <div className="p-6 space-y-4">
        {tasks.map((task, index) => (
          <div
            key={task.task_id || index}
            className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">{getStatusIcon(task.status)}</div>

              <div className="flex-1">
                <p className="text-gray-900 font-medium mb-2">{task.description}</p>

                <div className="flex flex-wrap items-center gap-3 text-sm">
                  {/* Priority Badge */}
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${getPriorityColor(task.priority)}`}>
                    {task.priority.toUpperCase()}
                  </span>

                  {/* Deadline */}
                  <div className="flex items-center gap-1 text-gray-600">
                    <Calendar className="w-4 h-4" />
                    <span>{formatDeadline(task.deadline)}</span>
                  </div>

                  {/* Action Required Flag */}
                  {task.requires_action_from_me && (
                    <div className="flex items-center gap-1 text-orange-600">
                      <Flag className="w-4 h-4" />
                      <span className="text-xs font-medium">Requires your action</span>
                    </div>
                  )}

                  {/* Status */}
                  <span className="text-xs text-gray-500">
                    Status: {task.status}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
