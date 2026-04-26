import { create } from 'zustand';

import { api } from '../services/api';
import type {
  FeedContext,
  IngestStatus,
  Player,
  ProfilePreferences,
  ReactionType,
  SavedView,
  Signal,
  SignalFilters,
  Team,
  UserProfile,
} from '../types';

interface SignalStore {
  filters: SignalFilters;
  signals: Signal[];
  hasMore: boolean;
  nextCursor: number | null;
  loadingInitial: boolean;
  loadingMore: boolean;
  players: Player[];
  teams: Team[];
  loading: boolean;
  error: string | null;
  ingestStatus: IngestStatus | null;
  feedContext: FeedContext | null;
  profile: UserProfile | null;
  setFilters: (filters: SignalFilters) => void;
  fetchSignals: () => Promise<void>;
  loadMore: () => Promise<void>;
  fetchPlayers: () => Promise<void>;
  fetchTeams: () => Promise<void>;
  reactToSignal: (signalId: number, reactionType: ReactionType) => Promise<void>;
  toggleFavorite: (signalId: number) => Promise<void>;
  fetchIngestStatus: () => Promise<void>;
  triggerIngest: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  toggleFollowPlayer: (playerId: number, currentlyFollowed: boolean) => Promise<void>;
  toggleFollowTeam: (teamId: number, currentlyFollowed: boolean) => Promise<void>;
  updatePreferences: (payload: Partial<ProfilePreferences>) => Promise<void>;
  saveView: (name: string) => Promise<void>;
  deleteSavedView: (savedViewId: number) => Promise<void>;
}

function applyReactionChange(signal: Signal, reactionType: ReactionType) {
  const nextSummary = { ...signal.reaction_summary };
  if (signal.user_reaction) {
    nextSummary[signal.user_reaction] = Math.max(0, nextSummary[signal.user_reaction] - 1);
  }
  const nextReaction = signal.user_reaction === reactionType ? null : reactionType;
  if (nextReaction) {
    nextSummary[nextReaction] += 1;
  }
  return {
    ...signal,
    user_reaction: nextReaction,
    reaction_summary: nextSummary,
  };
}

let fetchSeq = 0;

export const useSignalStore = create<SignalStore>((set, get) => ({
  filters: { sort: 'newest', feed: 'all' },
  signals: [],
  hasMore: false,
  nextCursor: null,
  loadingInitial: false,
  loadingMore: false,
  players: [],
  teams: [],
  loading: false,
  error: null,
  ingestStatus: null,
  feedContext: null,
  profile: null,

  setFilters: (filters) => set({ filters, signals: [], hasMore: false, nextCursor: null }),

  fetchSignals: async () => {
    const seq = ++fetchSeq;
    set({ loadingInitial: true, loading: true, error: null, signals: [], hasMore: false, nextCursor: null });
    try {
      const page = await api.getSignals(get().filters);
      if (seq !== fetchSeq) return;
      set({
        signals: page.items,
        hasMore: page.has_more,
        nextCursor: page.next_cursor,
        feedContext: page.feed_context,
        loadingInitial: false,
        loading: false,
      });
    } catch (error) {
      if (seq !== fetchSeq) return;
      set({ error: error instanceof Error ? error.message : 'Unknown error', loadingInitial: false, loading: false });
    }
  },

  loadMore: async () => {
    const { loadingMore, hasMore, nextCursor, filters, signals } = get();
    if (loadingMore || !hasMore || nextCursor == null) return;
    set({ loadingMore: true });
    try {
      const page = await api.getSignals(filters, nextCursor);
      set({
        signals: [...signals, ...page.items],
        hasMore: page.has_more,
        nextCursor: page.next_cursor,
        feedContext: page.feed_context,
        loadingMore: false,
      });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Load more failed.', loadingMore: false });
    }
  },

  fetchPlayers: async () => {
    set({ loading: true, error: null });
    try {
      const players = await api.getPlayers();
      set({ players, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', loading: false });
    }
  },

  fetchTeams: async () => {
    set({ loading: true, error: null });
    try {
      const teams = await api.getTeams();
      set({ teams, loading: false });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error', loading: false });
    }
  },

  reactToSignal: async (signalId, reactionType) => {
    const previousSignals = get().signals;
    const target = previousSignals.find((signal) => signal.id === signalId);
    if (!target) return;

    const optimisticSignals = previousSignals.map((signal) =>
      signal.id === signalId ? applyReactionChange(signal, reactionType) : signal,
    );
    set({ signals: optimisticSignals });

    try {
      if (target.user_reaction === reactionType) {
        await api.clearSignalReaction(signalId);
      } else {
        await api.setSignalReaction(signalId, reactionType);
      }
    } catch (error) {
      set({
        signals: previousSignals,
        error: error instanceof Error ? error.message : 'Reaction update failed.',
      });
      throw error;
    }
  },

  toggleFavorite: async (signalId) => {
    const previousSignals = get().signals;
    const target = previousSignals.find((s) => s.id === signalId);
    if (!target) return;

    const optimisticSignals = previousSignals.map((s) =>
      s.id === signalId ? { ...s, is_favorited: !s.is_favorited } : s,
    );
    set({ signals: optimisticSignals });

    try {
      if (target.is_favorited) {
        await api.removeFavorite(signalId);
      } else {
        await api.addFavorite(signalId);
      }
      if (get().profile) {
        await get().fetchProfile();
      }
    } catch (error) {
      set({
        signals: previousSignals,
        error: error instanceof Error ? error.message : 'Favorite update failed.',
      });
    }
  },

  fetchIngestStatus: async () => {
    try {
      const status = await api.getIngestStatus();
      set({ ingestStatus: status });
    } catch {
      // non-critical
    }
  },

  triggerIngest: async () => {
    try {
      await api.triggerIngest();
      set({
        ingestStatus: {
          status: 'running',
          last_updated: get().ingestStatus?.last_updated ?? null,
          started_at: new Date().toISOString(),
          finished_at: null,
          current_run_duration_seconds: 0,
          last_error: null,
          recent_runs: get().ingestStatus?.recent_runs ?? [],
        },
      });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Ingest trigger failed.' });
    }
  },

  fetchProfile: async () => {
    try {
      const profile = await api.getProfile();
      set({ profile });
    } catch {
      set({ profile: null });
    }
  },

  toggleFollowPlayer: async (playerId, currentlyFollowed) => {
    const profile = get().profile;
    if (!profile) return;
    const previousSignals = get().signals;
    const nextPlayers = currentlyFollowed
      ? profile.follows.players.filter((id) => id !== playerId)
      : [...profile.follows.players, playerId];
    const nextProfile = { ...profile, follows: { ...profile.follows, players: nextPlayers } };
    const nextSignals =
      get().filters.feed === 'following' && currentlyFollowed
        ? previousSignals.filter((signal) => signal.player_id !== playerId || nextProfile.follows.teams.includes(signal.team_id))
        : previousSignals;
    set({
      profile: nextProfile,
      signals: nextProfile.follows.players.length === 0 && nextProfile.follows.teams.length === 0 ? [] : nextSignals,
      hasMore: nextProfile.follows.players.length === 0 && nextProfile.follows.teams.length === 0 ? false : get().hasMore,
      nextCursor: nextProfile.follows.players.length === 0 && nextProfile.follows.teams.length === 0 ? null : get().nextCursor,
    });
    try {
      if (currentlyFollowed) {
        await api.unfollowPlayer(playerId);
      } else {
        await api.followPlayer(playerId);
      }
    } catch {
      set({ profile, signals: previousSignals });
    }
  },

  toggleFollowTeam: async (teamId, currentlyFollowed) => {
    const profile = get().profile;
    if (!profile) return;
    const previousSignals = get().signals;
    const nextTeams = currentlyFollowed
      ? profile.follows.teams.filter((id) => id !== teamId)
      : [...profile.follows.teams, teamId];
    const nextProfile = { ...profile, follows: { ...profile.follows, teams: nextTeams } };
    const nextSignals =
      get().filters.feed === 'following' && currentlyFollowed
        ? previousSignals.filter((signal) => signal.team_id !== teamId || nextProfile.follows.players.includes(signal.player_id ?? -1))
        : previousSignals;
    set({
      profile: nextProfile,
      signals: nextProfile.follows.players.length === 0 && nextProfile.follows.teams.length === 0 ? [] : nextSignals,
      hasMore: nextProfile.follows.players.length === 0 && nextProfile.follows.teams.length === 0 ? false : get().hasMore,
      nextCursor: nextProfile.follows.players.length === 0 && nextProfile.follows.teams.length === 0 ? null : get().nextCursor,
    });
    try {
      if (currentlyFollowed) {
        await api.unfollowTeam(teamId);
      } else {
        await api.followTeam(teamId);
      }
    } catch {
      set({ profile, signals: previousSignals });
    }
  },

  updatePreferences: async (payload) => {
    const profile = get().profile;
    if (!profile) return;
    const preferences = await api.updatePreferences(payload);
    set({ profile: { ...profile, preferences } });
  },

  saveView: async (name) => {
    const { filters, profile } = get();
    const savedView = await api.createSavedView({
      name,
      league: filters.league,
      signal_type: filters.signal_type,
      player: filters.player,
      sort_mode: filters.sort ?? 'newest',
      feed_mode: filters.feed ?? 'all',
    });
    set({
      profile: profile
        ? { ...profile, saved_views: [savedView, ...profile.saved_views] as SavedView[] }
        : profile,
    });
  },

  deleteSavedView: async (savedViewId) => {
    const profile = get().profile;
    if (!profile) return;
    await api.deleteSavedView(savedViewId);
    set({
      profile: {
        ...profile,
        saved_views: profile.saved_views.filter((view) => view.id !== savedViewId),
      },
    });
  },
}));
