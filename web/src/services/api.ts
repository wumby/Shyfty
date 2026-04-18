import type {
  Comment,
  MetricSeriesPoint,
  PaginatedSignals,
  Player,
  PlayerDetail,
  ReactionType,
  Signal,
  SignalFilters,
  SignalTrace,
  Team,
  TeamDetail,
  User,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8001/api';

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
  return response.json() as Promise<T>;
}

interface AuthSession {
  user: User | null;
}

export const api = {
  getSignals(filters: SignalFilters = {}, beforeId?: number) {
    const query = new URLSearchParams();
    if (filters.league) query.set('league', filters.league);
    if (filters.signal_type) query.set('signal_type', filters.signal_type);
    if (beforeId != null) query.set('before_id', String(beforeId));
    query.set('limit', '24');
    return request<PaginatedSignals>(`/signals?${query.toString()}`);
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
  getPlayerMetrics(id: string) {
    return request<MetricSeriesPoint[]>(`/players/${id}/metrics`);
  },
  getTeams() {
    return request<Team[]>('/teams');
  },
  getTeam(id: string) {
    return request<TeamDetail>(`/teams/${id}`);
  },
  getSignalTrace(id: number) {
    return request<SignalTrace>(`/debug/signals/${id}`);
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
  setSignalReaction(signalId: number, type: ReactionType) {
    return request(`/signals/${signalId}/reaction`, {
      method: 'PUT',
      body: JSON.stringify({ type }),
    });
  },
  clearSignalReaction(signalId: number) {
    return request<void>(`/signals/${signalId}/reaction`, { method: 'DELETE' });
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
  deleteComment(commentId: number) {
    return request<void>(`/comments/${commentId}`, { method: 'DELETE' });
  },
};
