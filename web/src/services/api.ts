import type {
  Comment,
  FeedMode,
  GameLogRow,
  IngestStatus,
  MetricSeriesPoint,
  PaginatedShyfts,
  Player,
  PlayerDetail,
  ProfilePreferences,
  ReactionType,
  SeasonAveragesRow,
  Shyft,
  ShyftFilters,
  ShyftTrace,
  Team,
  TeamDetail,
  User,
  UserProfile,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';
const CSRF_COOKIE_NAME = 'shyfty_csrf';

function getCookie(name: string): string | null {
  const encodedName = `${encodeURIComponent(name)}=`;
  for (const entry of document.cookie.split(';')) {
    const cookie = entry.trim();
    if (cookie.startsWith(encodedName)) {
      return decodeURIComponent(cookie.slice(encodedName.length));
    }
  }
  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const headers = new Headers(init?.headers ?? {});
  headers.set('Content-Type', 'application/json');
  if (method === 'POST' || method === 'PUT' || method === 'PATCH' || method === 'DELETE') {
    const csrfToken = getCookie(CSRF_COOKIE_NAME);
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: 'no-store',
    credentials: 'include',
    headers,
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
  getShyfts(filters: ShyftFilters = {}, beforeId?: number) {
    const query = new URLSearchParams();
    if (filters.league) query.set('league', filters.league);
    if (filters.shyft_type) query.set('shyft_type', filters.shyft_type);
    if (filters.player) query.set('player', filters.player);
    if (filters.sort) query.set('sort', filters.sort);
    if (filters.feed) query.set('feed', filters.feed);
    if (filters.date_from) query.set('date_from', filters.date_from);
    if (filters.date_to) query.set('date_to', filters.date_to);
    if (beforeId != null) query.set('before_id', String(beforeId));
    query.set('limit', '24');
    return request<PaginatedShyfts>(`/shyfts?${query.toString()}`);
  },
  getShyft(id: number) {
    return request<ShyftTrace>(`/shyfts/${id}`);
  },
  getPlayers() {
    return request<Player[]>('/players');
  },
  getPlayer(id: string) {
    return request<PlayerDetail>(`/players/${id}`);
  },
  getPlayerShyfts(id: string) {
    return request<Shyft[]>(`/players/${id}/shyfts`);
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
  getShyftTrace(id: number) {
    return request<ShyftTrace>(`/shyfts/${id}`);
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
  changePassword(payload: { current_password: string; new_password: string; confirm_new_password: string }) {
    return request<{ message: string }>('/auth/password', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },
  forgotPassword(email: string) {
    return request<{ message: string }>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },
  resetPassword(token: string, new_password: string, confirm_password: string) {
    return request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password, confirm_password }),
    });
  },
  setShyftReaction(shyftId: number, type: ReactionType) {
    return request(`/shyfts/${shyftId}/reaction`, {
      method: 'PUT',
      body: JSON.stringify({ type }),
    });
  },
  clearShyftReaction(shyftId: number) {
    return request<void>(`/shyfts/${shyftId}/reaction`, { method: 'DELETE' });
  },
  getTrendingShyfts(limit = 12) {
    return request<Shyft[]>(`/shyfts/trending?limit=${limit}`);
  },
  getComments(shyftId: number) {
    return request<Comment[]>(`/shyfts/${shyftId}/comments`);
  },
  postComment(shyftId: number, body: string) {
    return request<Comment>(`/shyfts/${shyftId}/comments`, {
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
  updateProfile(payload: { display_name: string | null }) {
    return request<UserProfile>('/profile', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },
};
