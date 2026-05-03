import { create } from 'zustand';

import { api } from '../services/api';
import type {
  FeedContext,
  FeedItem,
  IngestStatus,
  Player,
  ProfilePreferences,
  ReactionType,
  Signal,
  SignalFilters,
  Team,
  UserProfile,
  ReactionEntry,
} from '../types';

interface SignalStore {
  filters: SignalFilters;
  signals: FeedItem[];
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
  signalMetaById: Record<number, Pick<Signal, 'comment_count' | 'reaction_summary' | 'user_reaction' | 'reactions' | 'user_reactions'>>;
  setFilters: (filters: SignalFilters) => void;
  fetchSignals: () => Promise<void>;
  loadMore: () => Promise<void>;
  fetchPlayers: () => Promise<void>;
  fetchTeams: () => Promise<void>;
  reactToSignal: (signalId: number, reactionType: ReactionType) => Promise<void>;
  setSignalCommentCount: (signalId: number, count: number) => void;
  fetchIngestStatus: () => Promise<void>;
  triggerIngest: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  toggleFollowPlayer: (playerId: number, currentlyFollowed: boolean) => Promise<void>;
  toggleFollowTeam: (teamId: number, currentlyFollowed: boolean) => Promise<void>;
  updatePreferences: (payload: Partial<ProfilePreferences>) => Promise<void>;
}

function normalizeReactions(signal: Signal): ReactionEntry[] {
  if (signal.reactions && signal.reactions.length > 0) {
    return signal.reactions.map((item) => ({
      emoji: item.emoji,
      count: item.count,
      reactedByCurrentUser:
        item.reactedByCurrentUser ??
        (item as unknown as { reacted_by_current_user?: boolean }).reacted_by_current_user ??
        false,
    }));
  }
  const userSet = new Set<string>(signal.user_reactions ?? []);
  const legacyMap: Array<[string, number]> = [
    ['👍', signal.reaction_summary.agree ?? 0],
    ['🔥', signal.reaction_summary.strong ?? 0],
    ['👎', signal.reaction_summary.risky ?? 0],
  ];
  return legacyMap
    .filter(([, count]) => count > 0)
    .map(([emoji, count]) => ({ emoji, count, reactedByCurrentUser: userSet.has(emoji) }));
}

function applyReactionChange(signal: Signal, emoji: ReactionType) {
  const reactions = normalizeReactions(signal);
  const existing = reactions.find((item) => item.emoji === emoji);
  const nextReactions = reactions
    .map((item) => {
      if (item.emoji !== emoji) return item;
      if (item.reactedByCurrentUser) {
        return { ...item, count: Math.max(0, item.count - 1), reactedByCurrentUser: false };
      }
      return { ...item, count: item.count + 1, reactedByCurrentUser: true };
    })
    .filter((item) => item.count > 0);
  if (!existing) {
    nextReactions.push({ emoji, count: 1, reactedByCurrentUser: true });
  }

  const isLegacyEmoji = emoji === '👍' || emoji === '🔥' || emoji === '👎';
  return {
    ...signal,
    reactions: nextReactions,
    user_reactions: nextReactions.filter((item) => item.reactedByCurrentUser).map((item) => item.emoji),
    user_reaction: isLegacyEmoji ? emoji : signal.user_reaction,
    reaction_summary: {
      agree: nextReactions.find((item) => item.emoji === '👍')?.count ?? 0,
      strong: nextReactions.find((item) => item.emoji === '🔥')?.count ?? 0,
      risky: nextReactions.find((item) => item.emoji === '👎')?.count ?? 0,
    },
  };
}

function isSignal(item: FeedItem): item is Signal {
  return item.type !== 'cascade';
}

let fetchSeq = 0;

function extractSignalMeta(signal: Signal): Pick<Signal, 'comment_count' | 'reaction_summary' | 'user_reaction' | 'reactions' | 'user_reactions'> {
  return {
    comment_count: signal.comment_count ?? 0,
    reaction_summary: signal.reaction_summary,
    user_reaction: signal.user_reaction ?? null,
    reactions: normalizeReactions(signal),
    user_reactions: signal.user_reactions ?? [],
  };
}

function mergeSignalMeta(
  current: Record<number, Pick<Signal, 'comment_count' | 'reaction_summary' | 'user_reaction' | 'reactions' | 'user_reactions'>>,
  signals: FeedItem[],
) {
  const next = { ...current };
  for (const item of signals) {
    if (!isSignal(item)) continue;
    next[item.id] = extractSignalMeta(item);
  }
  return next;
}

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
  signalMetaById: {},

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
        signalMetaById: mergeSignalMeta(get().signalMetaById, page.items),
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
        signalMetaById: mergeSignalMeta(get().signalMetaById, page.items),
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
    const previousMeta = get().signalMetaById;
    const target = previousSignals.find((signal): signal is Signal => isSignal(signal) && signal.id === signalId);
    const metaTarget = previousMeta[signalId];
    const sourceSignal: Signal | null = target
      ? target
      : metaTarget
        ? {
            id: signalId,
            type: 'signal',
            subject_type: 'player',
            player_id: null,
            team_id: 0,
            game_id: 0,
            player_name: '',
            team_name: '',
            league_name: '',
            signal_type: 'SHIFT',
            severity: 'SHIFT',
            metric_name: '',
            current_value: 0,
            baseline_value: 0,
            performance: null,
            deviation: null,
            z_score: 0,
            signal_score: 0,
            explanation: '',
            movement_pct: null,
            streak: 1,
            reaction_summary: metaTarget.reaction_summary,
            user_reaction: metaTarget.user_reaction,
            reactions: metaTarget.reactions,
            user_reactions: metaTarget.user_reactions,
            comment_count: metaTarget.comment_count,
            created_at: new Date(0).toISOString(),
          }
        : null;
    if (!sourceSignal) return;

    const optimisticSignal = applyReactionChange(sourceSignal, reactionType);
    const optimisticSignals = previousSignals.map((signal) =>
      isSignal(signal) && signal.id === signalId ? optimisticSignal : signal,
    );
    set({
      signals: optimisticSignals,
      signalMetaById: {
        ...previousMeta,
        [signalId]: extractSignalMeta(optimisticSignal),
      },
    });

    const wasReacted = normalizeReactions(sourceSignal).some((item) => item.emoji === reactionType && item.reactedByCurrentUser);
    try {
      if (wasReacted) {
        await api.clearSignalReaction(signalId, reactionType);
      } else {
        await api.setSignalReaction(signalId, reactionType);
      }
    } catch (error) {
      set({
        signals: previousSignals,
        signalMetaById: previousMeta,
        error: error instanceof Error ? error.message : 'Reaction update failed.',
      });
      throw error;
    }
  },

  setSignalCommentCount: (signalId, count) => {
    const prevMeta = get().signalMetaById;
    const existing = prevMeta[signalId];
    set({
      signals: get().signals.map((item) =>
        isSignal(item) && item.id === signalId
          ? { ...item, comment_count: count }
          : item,
      ),
      signalMetaById: {
        ...prevMeta,
        [signalId]: {
          comment_count: count,
          reaction_summary: existing?.reaction_summary ?? { agree: 0, strong: 0, risky: 0 },
          user_reaction: existing?.user_reaction ?? null,
          reactions: existing?.reactions ?? [],
          user_reactions: existing?.user_reactions ?? [],
        },
      },
    });
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
    const isFollowingFeed = get().filters.feed === 'following';
    const hasAnyFollows = nextProfile.follows.players.length > 0 || nextProfile.follows.teams.length > 0;
    const nextSignals =
      isFollowingFeed && currentlyFollowed
        ? previousSignals.filter(
            (signal) =>
              !isSignal(signal) ||
              signal.player_id !== playerId ||
              (signal.subject_type === 'team' && nextProfile.follows.teams.includes(signal.team_id)),
          )
        : previousSignals;
    set({
      profile: nextProfile,
      signals: isFollowingFeed && !hasAnyFollows ? [] : nextSignals,
      hasMore: isFollowingFeed && !hasAnyFollows ? false : get().hasMore,
      nextCursor: isFollowingFeed && !hasAnyFollows ? null : get().nextCursor,
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
    const isFollowingFeed = get().filters.feed === 'following';
    const hasAnyFollows = nextProfile.follows.players.length > 0 || nextProfile.follows.teams.length > 0;
    const nextSignals =
      isFollowingFeed && currentlyFollowed
        ? previousSignals.filter(
            (signal) =>
              !isSignal(signal) ||
              signal.team_id !== teamId ||
              (signal.subject_type === 'player' && nextProfile.follows.players.includes(signal.player_id ?? -1)),
          )
        : previousSignals;
    set({
      profile: nextProfile,
      signals: isFollowingFeed && !hasAnyFollows ? [] : nextSignals,
      hasMore: isFollowingFeed && !hasAnyFollows ? false : get().hasMore,
      nextCursor: isFollowingFeed && !hasAnyFollows ? null : get().nextCursor,
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

}));
