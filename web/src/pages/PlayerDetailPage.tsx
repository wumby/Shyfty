import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { PlayerHeader } from '../components/PlayerHeader';
import { SignalFeed } from '../components/SignalFeed';
import { TrendChart } from '../components/TrendChart';
import { api } from '../services/api';
import type { MetricSeriesPoint, PlayerDetail, Signal } from '../types';

export function PlayerDetailPage() {
  const { id = '' } = useParams();
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [metrics, setMetrics] = useState<MetricSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [playerResponse, signalResponse, metricResponse] = await Promise.all([
          api.getPlayer(id),
          api.getPlayerSignals(id),
          api.getPlayerMetrics(id),
        ]);
        setPlayer(playerResponse);
        setSignals(signalResponse);
        setMetrics(metricResponse);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id]);

  if (loading) return <LoadingState />;
  if (error || !player) return <EmptyState title="Player unavailable" copy={error ?? 'No player found.'} />;

  return (
    <div className="space-y-6">
      <PlayerHeader player={player} />
      <TrendChart data={metrics} />
      <div>
        <div className="mb-3 px-1">
          <div className="eyebrow">Active Signals · {signals.length}</div>
        </div>
        <SignalFeed signals={signals} />
      </div>
    </div>
  );
}
