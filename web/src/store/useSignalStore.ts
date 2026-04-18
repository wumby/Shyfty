import { create } from 'zustand';

import { api } from '../services/api';
import type { Player, ReactionType, Signal, SignalFilters, Team } from '../types';

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
  setFilters: (filters: SignalFilters) => void;
  fetchSignals: () => Promise<void>;
  loadMore: () => Promise<void>;
  fetchPlayers: () => Promise<void>;
  fetchTeams: () => Promise<void>;
  reactToSignal: (signalId: number, reactionType: ReactionType) => Promise<void>;
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

export const useSignalStore = create<SignalStore>((set, get) => ({
  filters: {},
  signals: [],
  hasMore: false,
  nextCursor: null,
  loadingInitial: false,
  loadingMore: false,
  players: [],
  teams: [],
  loading: false,
  error: null,

  setFilters: (filters) => set({ filters }),

  fetchSignals: async () => {
    set({ loadingInitial: true, loading: true, error: null, signals: [], hasMore: false, nextCursor: null });
    try {
      const page = await api.getSignals(get().filters);
      set({ signals: page.items, hasMore: page.has_more, nextCursor: page.next_cursor, loadingInitial: false, loading: false });
    } catch (error) {
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
}));
