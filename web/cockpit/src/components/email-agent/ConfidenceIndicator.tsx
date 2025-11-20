interface ConfidenceIndicatorProps {
  confidence: number | null; // 0-1 range
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ConfidenceIndicator({
  confidence,
  showPercentage = true,
  size = 'md',
}: ConfidenceIndicatorProps) {
  if (confidence === null) {
    return <span className="text-sm text-gray-500">N/A</span>;
  }

  // Determine color based on thresholds
  const getColorClass = (conf: number): string => {
    if (conf >= 0.9) return 'bg-green-500';
    if (conf >= 0.65) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  // Size classes
  const sizeClasses = {
    sm: 'w-12 h-1.5',
    md: 'w-16 h-2',
    lg: 'w-24 h-3',
  };

  const percentage = Math.round(confidence * 100);

  return (
    <div className="flex items-center gap-2">
      <div className={`${sizeClasses[size]} bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`h-full rounded-full transition-all ${getColorClass(confidence)}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
      {showPercentage && (
        <span className="text-sm text-gray-600 font-medium">{percentage}%</span>
      )}
    </div>
  );
}
