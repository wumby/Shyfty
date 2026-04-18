import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { MetricSeriesPoint } from '../types';

interface TrendChartProps {
  data: MetricSeriesPoint[];
}

export function TrendChart({ data }: TrendChartProps) {
  const normalized = data.map((point) => ({
    game_date: new Date(point.game_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    ...point.metrics,
  }));

  const firstMetric = Object.keys(data[0]?.metrics ?? {})[0];

  if (!firstMetric) {
    return null;
  }

  return (
    <div className="panel-surface h-72 p-5">
      <div className="eyebrow">Performance arc</div>
      <div className="mb-4 mt-2 text-sm text-muted">Recent {firstMetric.replace('_', ' ')} trend</div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={normalized}>
          <CartesianGrid stroke="rgba(139, 160, 185, 0.16)" strokeDasharray="4 4" />
          <XAxis dataKey="game_date" stroke="#8ba0b9" />
          <YAxis stroke="#8ba0b9" />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(5, 13, 25, 0.95)',
              borderColor: 'rgba(166, 194, 225, 0.2)',
              borderRadius: '16px',
            }}
          />
          <Line dataKey={firstMetric} type="monotone" stroke="#f97316" strokeWidth={3} dot={{ r: 4, fill: '#f97316' }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
