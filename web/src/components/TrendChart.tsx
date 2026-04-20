import { CartesianGrid, LabelList, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from 'recharts';

import type { MetricSeriesPoint, Signal } from '../types';
import { formatEventDate } from '../lib/signalFormat';

interface TrendChartProps {
  data: MetricSeriesPoint[];
  signals?: Signal[];
}

export function TrendChart({ data, signals = [] }: TrendChartProps) {
  const firstMetric = Object.keys(data[0]?.metrics ?? {})[0];

  const metricSeries = data.map((point) => point.metrics[firstMetric] ?? 0);
  const baseline = metricSeries.reduce((sum, value) => sum + value, 0) / Math.max(metricSeries.length, 1);
  const highlightSignals = signals
    .slice()
    .sort((left, right) => Math.abs(right.z_score) - Math.abs(left.z_score))
    .slice(0, 3);

  const normalized = data.map((point) => {
    const metricValue = point.metrics[firstMetric] ?? 0;
    const matchingSignal = highlightSignals.find((signal) => signal.event_date === point.game_date);

    return {
      game_date: new Date(point.game_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      metricValue,
      baseline,
      annotation: matchingSignal ? matchingSignal.signal_type : '',
      signalPoint: matchingSignal ? metricValue : null,
    };
  });

  if (!firstMetric) {
    return null;
  }

  return (
    <div className="panel-surface h-[22rem] p-5">
      <div className="eyebrow">Performance Arc</div>
      <div className="mb-4 mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        <span>Recent {firstMetric.replace('_', ' ')} trend</span>
        <span>Baseline {baseline.toFixed(1)}</span>
        {highlightSignals[0] ? <span>Key move {formatEventDate(highlightSignals[0].event_date ?? highlightSignals[0].created_at)}</span> : null}
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={normalized}>
          <CartesianGrid stroke="rgba(139, 160, 185, 0.16)" strokeDasharray="4 4" />
          <XAxis dataKey="game_date" stroke="#8ba0b9" />
          <YAxis stroke="#8ba0b9" />
          <ReferenceLine y={baseline} stroke="rgba(255,255,255,0.28)" strokeDasharray="5 5" />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(5, 13, 25, 0.95)',
              borderColor: 'rgba(166, 194, 225, 0.2)',
              borderRadius: '16px',
            }}
          />
          <Line dataKey="metricValue" type="monotone" stroke="#f97316" strokeWidth={3} dot={{ r: 3, fill: '#f97316' }} activeDot={{ r: 5 }} />
          <Line dataKey="baseline" type="monotone" stroke="rgba(246,242,232,0.45)" strokeWidth={2} dot={false} />
          <Scatter data={normalized.filter((point) => point.signalPoint != null)} dataKey="signalPoint" fill="#ffd8bd">
            <LabelList dataKey="annotation" position="top" className="fill-[#ffd8bd]" fontSize={10} />
          </Scatter>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
