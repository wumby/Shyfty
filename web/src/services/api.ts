import type {
  Comment,
  FeedMode,
  GameLogRow,
  IngestStatus,
  MetricSeriesPoint,
  PaginatedSignals,
  Player,
  PlayerDetail,
  ProfilePreferences,
  ReactionType,
  SeasonAveragesRow,
  Signal,
  SignalFilters,
  SignalTrace,
  Team,
  TeamDetail,
  User,
  UserProfile,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    let detail = `API request failed: ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore body parse errors
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.toLowerCase().includes('application/json')) {
    const raw = await response.text();
    if (raw.trim().length === 0) {
      return undefined as T;
    }
    return raw as T;
  }

  const raw = await response.text();
  if (raw.trim().length === 0) {
    return undefined as T;
  }
  return JSON.parse(raw) as T;
}

interface AuthSession {
  user: User | null;
}

export const api = {
  getSignals(filters: SignalFilters = {}, beforeId?: number) {
    const query = new URLSearchParams();
    if (filters.league) query.set('league', filters.league);
    if (filters.signal_type) query.set('signal_type', filters.signal_type);
    if (filters.player) query.set('player', filters.player);
    if (filters.sort) query.set('sort', filters.sort);
    if (filters.feed) query.set('feed', filters.feed);
    if (filters.date_from) query.set('date_from', filters.date_from);
    if (filters.date_to) query.set('date_to', filters.date_to);
    if (beforeId != null) query.set('before_id', String(beforeId));
    query.set('limit', '24');
    return request<PaginatedSignals>(`/signals?${query.toString()}`);
  },
  getSignal(id: number) {
    return request<SignalTrace>(`/signals/${id}`);
  },
  getPlayers() {
    return request<Player[]>('/players');
  },
  getPlayer(id: string) {
    return request<PlayerDetail>(`/players/${id}`);
  },
  getPlayerSignals(id: string) {
    return request<Signal[]>(`/players/${id}/signals`);
  },
  getPlayerGamelog(id: string, season?: string) {
    const query = season ? `?season=${encodeURIComponent(season)}` : '';
    return request<GameLogRow[]>(`/players/${id}/gamelog${query}`);
  },
  getPlayerSeasonAverages(id: string) {
    return request<SeasonAveragesRow[]>(`/players/${id}/season-averages`);
  },
  getPlayerMetrics(id: string) {
    return request<MetricSeriesPoint[]>(`/players/${id}/metrics`);
  },
  followPlayer(playerId: number) {
    return request<void>(`/players/${playerId}/follow`, { method: 'POST' });
  },
  unfollowPlayer(playerId: number) {
    return request<void>(`/players/${playerId}/follow`, { method: 'DELETE' });
  },
  getTeams() {
    return request<Team[]>('/teams');
  },
  getTeam(id: string) {
    return request<TeamDetail>(`/teams/${id}`);
  },
  followTeam(teamId: number) {
    return request<void>(`/teams/${teamId}/follow`, { method: 'POST' });
  },
  unfollowTeam(teamId: number) {
    return request<void>(`/teams/${teamId}/follow`, { method: 'DELETE' });
  },
  getSignalTrace(id: number) {
    return request<SignalTrace>(`/signals/${id}`);
  },
  getSession() {
    return request<AuthSession>('/auth/me');
  },
  signIn(email: string, password: string) {
    return request<AuthSession>('/auth/signin', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },
  signUp(email: string, password: string) {
    return request<AuthSession>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },
  signOut() {
    return request<void>('/auth/signout', { method: 'POST' });
  },
  async setSignalReaction(signalId: number, emoji: ReactionType) {
    try {
      return await request(`/signals/${signalId}/reactions`, {
        method: 'POST',
        body: JSON.stringify({ emoji }),
      });
    } catch {
      const legacyMap: Record<string, string> = { '👍': 'agree', '🔥': 'strong', '👎': 'risky' };
      const legacyType = legacyMap[emoji];
      if (!legacyType) throw new Error('This server only supports legacy reactions.');
      return request(`/signals/${signalId}/reaction`, {
        method: 'PUT',
        body: JSON.stringify({ type: legacyType }),
      });
    }
  },
  async clearSignalReaction(signalId: number, emoji: ReactionType) {
    try {
      return await request<void>(`/signals/${signalId}/reactions/${encodeURIComponent(emoji)}`, { method: 'DELETE' });
    } catch {
      const legacyMap: Record<string, string> = { '👍': 'agree', '🔥': 'strong', '👎': 'risky' };
      const legacyType = legacyMap[emoji];
      if (!legacyType) throw new Error('This server only supports legacy reactions.');
      return request<void>(`/signals/${signalId}/reaction`, { method: 'DELETE' });
    }
  },
  getTrendingSignals(limit = 12) {
    return request<Signal[]>(`/signals/trending?limit=${limit}`);
  },
  getComments(signalId: number) {
    return request<Comment[]>(`/signals/${signalId}/comments`);
  },
  postComment(signalId: number, body: string) {
    return request<Comment>(`/signals/${signalId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    });
  },
  updateComment(commentId: number, body: string) {
    return request<Comment>(`/comments/${commentId}`, {
      method: 'PUT',
      body: JSON.stringify({ body }),
    });
  },
  reportComment(commentId: number, reason: string, notes?: string) {
    return request<{ comment_id: number; status: string; open_report_count: number }>(`/comments/${commentId}/report`, {
      method: 'POST',
      body: JSON.stringify({ reason, notes }),
    });
  },
  deleteComment(commentId: number) {
    return request<void>(`/comments/${commentId}`, { method: 'DELETE' });
  },
  getIngestStatus() {
    return request<IngestStatus>('/ingest/status');
  },
  triggerIngest() {
    return request<{ message: string }>('/ingest/trigger', { method: 'POST' });
  },
  getProfile() {
    return request<UserProfile>('/profile');
  },
  updatePreferences(payload: Partial<ProfilePreferences>) {
    return request<ProfilePreferences>('/profile/preferences', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },
};
