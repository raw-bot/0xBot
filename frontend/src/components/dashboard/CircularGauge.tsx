interface CircularGaugeProps {
  value: number;
  maxValue?: number;
  radius: number;
  strokeWidth: number;
  color: string;
  children: React.ReactNode;
}

export default function CircularGauge({
  value,
  maxValue = 100,
  radius,
  strokeWidth,
  color,
  children,
}: CircularGaugeProps): JSX.Element {
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / maxValue) * circumference;
  const size = (radius + strokeWidth) * 2;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="-rotate-90" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(0,0,0,0.08)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
}
