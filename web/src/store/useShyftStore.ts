import { create } from 'zustand';

import { api } from '../services/api';
import type {
  FeedContext,
  FeedItem,
  IngestStatus,
  Player,
  ProfilePreferences,
  ReactionType,
  ShyftReaction,
  Shyft,
  ShyftFilters,
  Team,
  UserProfile,
  ReactionEntry,
} from '../types';
import { SHYFT_REACTION_ORDER } from '../types';

interface ShyftStore {
  filters: ShyftFilters;
  shyfts: FeedItem[];
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
  shyftMetaById: Record<number, Pick<Shyft, 'comment_count' | 'reaction_summary' | 'user_reaction' | 'reactions' | 'user_reactions'>>;

  setFilters: (filters: ShyftFilters) => void;
  fetchShyfts: () => Promise<void>;
  loadMore: () => Promise<void>;
  fetchPlayers: () => Promise<void>;
  fetchTeams: () => Promise<void>;
  reactToShyft: (shyftId: number, reactionType: ReactionType) => Promise<void>;
  setShyftCommentCount: (shyftId: number, count: number) => void;
  setShyftGroupCommentCount: (signalIds: number[], count: number) => void;
  mergeShyftMeta: (signal: Shyft) => void;
  fetchIngestStatus: () => Promise<void>;
  triggerIngest: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  toggleFollowPlayer: (playerId: number, currentlyFollowed: boolean) => Promise<void>;
  toggleFollowTeam: (teamId: number, currentlyFollowed: boolean) => Promise<void>;
  updatePreferences: (payload: Partial<ProfilePreferences>) => Promise<void>;
}

function normalizeReactions(signal: Shyft): ReactionEntry[] {
  const userSet = new Set<ShyftReaction>(signal.user_reactions ?? (signal.user_reaction ? [signal.user_reaction] : []));

  if (signal.reactions && signal.reactions.length > 0) {
    const byType = new Map(signal.reactions.map((r) => [r.type, r]));
    return SHYFT_REACTION_ORDER.map((type) => {
      const entry = byType.get(type);
      return {
        type,
        count: entry?.count ?? 0,
        reactedByCurrentUser: entry?.reactedByCurrentUser ?? userSet.has(type),
      };
    });
  }

  return SHYFT_REACTION_ORDER.map((type) => {
    const summaryKey = type === 'SHYFT_UP' ? 'shyft_up' : type === 'SHYFT_DOWN' ? 'shyft_down' : 'shyft_eye';
    return {
      type,
      count: signal.reaction_summary[summaryKey] ?? 0,
      reactedByCurrentUser: userSet.has(type),
    };
  });
}

function applyReactionChange(signal: Shyft, reactionType: ReactionType) {
  const reactions = normalizeReactions(signal);
  const isTogglingOff = reactions.find((r) => r.type === reactionType)?.reactedByCurrentUser ?? false;

  const nextReactions: ReactionEntry[] = SHYFT_REACTION_ORDER.map((type) => {
    const current = reactions.find((r) => r.type === type) ?? { type, count: 0, reactedByCurrentUser: false };
    if (type === reactionType) {
      return isTogglingOff
        ? { ...current, count: Math.max(0, current.count - 1), reactedByCurrentUser: false }
        : { ...current, count: current.count + 1, reactedByCurrentUser: true };
    }
    // Switching from another reaction: remove it
    if (current.reactedByCurrentUser) {
      return { ...current, count: Math.max(0, current.count - 1), reactedByCurrentUser: false };
    }
    return current;
  });

  const nextUserReaction = isTogglingOff ? null : reactionType;
  return {
    ...signal,
    reactions: nextReactions,
    user_reactions: nextUserReaction ? [nextUserReaction] : [],
    user_reaction: nextUserReaction,
    reaction_summary: {
      shyft_up: nextReactions.find((r) => r.type === 'SHYFT_UP')?.count ?? 0,
      shyft_down: nextReactions.find((r) => r.type === 'SHYFT_DOWN')?.count ?? 0,
      shyft_eye: nextReactions.find((r) => r.type === 'SHYFT_EYE')?.count ?? 0,
    },
  };
}

function isShyft(item: FeedItem): item is Shyft {
  return item.type !== 'cascade';
}

function patchFeedItem(item: FeedItem, shyftId: number, patch: Partial<Pick<Shyft, 'comment_count' | 'reaction_summary' | 'user_reaction' | 'reactions' | 'user_reactions'>>): FeedItem {
  if (isShyft(item)) {
    return item.id === shyftId ? { ...item, ...patch } : item;
  }

  return {
    ...item,
    underlying_shyfts: item.underlying_shyfts.map((signal) =>
      signal.id === shyftId ? { ...signal, ...patch } : signal,
    ),
  };
}

let fetchSeq = 0;

function filtersKey(filters: ShyftFilters): string {
  return JSON.stringify({
    league: filters.league ?? null,
    shyft_type: filters.shyft_type ?? null,
    player: filters.player ?? null,
    sort: filters.sort ?? null,
    feed: filters.feed ?? null,
    date_from: filters.date_from ?? null,
    date_to: filters.date_to ?? null,
  });
}

function sameFilters(left: ShyftFilters, right: ShyftFilters): boolean {
  return filtersKey(left) === filtersKey(right);
}

function extractShyftMeta(signal: Shyft): Pick<Shyft, 'comment_count' | 'reaction_summary' | 'user_reaction' | 'reactions' | 'user_reactions'> {
  const reactions = normalizeReactions(signal);
  return {
    comment_count: signal.comment_count ?? 0,
    reaction_summary: signal.reaction_summary,
    user_reaction: signal.user_reaction ?? null,
    reactions,
    user_reactions: reactions.filter((item) => item.reactedByCurrentUser).map((item) => item.type),
  };
}

function mergeShyftMeta(
  current: Record<number, Pick<Shyft, 'comment_count' | 'reaction_summary' | 'user_reaction' | 'reactions' | 'user_reactions'>>,
  shyfts: FeedItem[],
) {
  const next = { ...current };
  for (const item of shyfts) {
    if (!isShyft(item)) continue;
    next[item.id] = extractShyftMeta(item);
  }
  return next;
}

export const useShyftStore = create<ShyftStore>((set, get) => ({
  filters: { sort: 'newest', feed: 'all' },
  shyfts: [],
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
  shyftMetaById: {},

  setFilters: (filters) => {
    if (sameFilters(get().filters, filters)) return;
    set({ filters, shyfts: [], hasMore: false, nextCursor: null });
  },

  fetchShyfts: async () => {
    const seq = ++fetchSeq;
    set({ loadingInitial: true, loadingMore: false, loading: true, error: null, shyfts: [], hasMore: false, nextCursor: null });
    try {
      const page = await api.getShyfts(get().filters);
      if (seq !== fetchSeq) return;
      set({
        shyfts: page.items,
        hasMore: page.has_more,
        nextCursor: page.next_cursor,
        feedContext: page.feed_context,
        shyftMetaById: mergeShyftMeta(get().shyftMetaById, page.items),
        loadingInitial: false,
        loading: false,
      });
    } catch (error) {
      if (seq !== fetchSeq) return;
      set({ error: error instanceof Error ? error.message : 'Unknown error', loadingInitial: false, loading: false });
    }
  },

  loadMore: async () => {
    const { loadingMore, hasMore, nextCursor, filters, shyfts } = get();
    if (loadingMore || !hasMore || nextCursor == null) return;
    const seq = fetchSeq;
    const expectedFilters = filtersKey(filters);
    set({ loadingMore: true });
    try {
      const page = await api.getShyfts(filters, nextCursor);
      if (seq !== fetchSeq || filtersKey(get().filters) !== expectedFilters) {
        set({ loadingMore: false });
        return;
      }
      set({
        shyfts: [...shyfts, ...page.items],
        hasMore: page.has_more,
        nextCursor: page.next_cursor,
        feedContext: page.feed_context,
        shyftMetaById: mergeShyftMeta(get().shyftMetaById, page.items),
        loadingMore: false,
      });
    } catch (error) {
      if (seq !== fetchSeq || filtersKey(get().filters) !== expectedFilters) {
        set({ loadingMore: false });
        return;
      }
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

  reactToShyft: async (shyftId, reactionType) => {
    const previousShyfts = get().shyfts;
    const previousMeta = get().shyftMetaById;
    const target = previousShyfts.find((signal): signal is Shyft => isShyft(signal) && signal.id === shyftId);
    const metaTarget = previousMeta[shyftId];
    const sourceSignal: Shyft | null = target
      ? target
      : metaTarget
        ? {
            id: shyftId,
            type: 'shyft',
            subject_type: 'player',
            player_id: null,
            team_id: 0,
            game_id: 0,
            player_name: '',
            team_name: '',
            league_name: '',
            shyft_type: 'SHIFT',
            severity: 'SHIFT',
            metric_name: '',
            current_value: 0,
            baseline_value: 0,
            performance: null,
            deviation: null,
            z_score: 0,
            shyft_score: 0,
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
    const optimisticMeta = extractShyftMeta(optimisticSignal);
    const optimisticSignals = previousShyfts.map((signal) => patchFeedItem(signal, shyftId, optimisticMeta));
    set({
      shyfts: optimisticSignals,
      shyftMetaById: {
        ...previousMeta,
        [shyftId]: optimisticMeta,
      },
    });

    const wasReacted = normalizeReactions(sourceSignal).some((item) => item.type === reactionType && item.reactedByCurrentUser);
    try {
      if (wasReacted) {
        await api.clearShyftReaction(shyftId);
      } else {
        await api.setShyftReaction(shyftId, reactionType);
      }
    } catch (error) {
      set({
        shyfts: previousShyfts,
        shyftMetaById: previousMeta,
        error: error instanceof Error ? error.message : 'Reaction update failed.',
      });
      throw error;
    }
  },

  setShyftCommentCount: (shyftId, count) => {
    get().setShyftGroupCommentCount([shyftId], count);
  },

  setShyftGroupCommentCount: (signalIds, count) => {
    const ids = [...new Set(signalIds)].filter((id) => Number.isFinite(id));
    if (ids.length === 0) return;
    const prevMeta = get().shyftMetaById;
    const patch = { comment_count: count };
    const nextMeta = { ...prevMeta };
    for (const shyftId of ids) {
      const existing = prevMeta[shyftId];
      nextMeta[shyftId] = {
        comment_count: count,
        reaction_summary: existing?.reaction_summary ?? { shyft_up: 0, shyft_down: 0, shyft_eye: 0 },
        user_reaction: existing?.user_reaction ?? null,
        reactions: existing?.reactions ?? [],
        user_reactions: existing?.user_reactions ?? [],
      };
    }
    set({
      shyfts: get().shyfts.map((item) => ids.reduce((nextItem, shyftId) => patchFeedItem(nextItem, shyftId, patch), item)),
      shyftMetaById: nextMeta,
    });
  },

  mergeShyftMeta: (signal) => {
    const meta = extractShyftMeta(signal);
    set({
      shyfts: get().shyfts.map((item) => patchFeedItem(item, signal.id, meta)),
      shyftMetaById: {
        ...get().shyftMetaById,
        [signal.id]: meta,
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
    const previousShyfts = get().shyfts;
    const nextPlayers = currentlyFollowed
      ? profile.follows.players.filter((id) => id !== playerId)
      : [...profile.follows.players, playerId];
    const nextProfile = { ...profile, follows: { ...profile.follows, players: nextPlayers } };
    const isFollowingFeed = get().filters.feed === 'following';
    const hasAnyFollows = nextProfile.follows.players.length > 0 || nextProfile.follows.teams.length > 0;
    const nextShyfts =
      isFollowingFeed && currentlyFollowed
        ? previousShyfts.filter(
            (signal) =>
              !isShyft(signal) ||
              signal.player_id !== playerId ||
              (signal.subject_type === 'team' && nextProfile.follows.teams.includes(signal.team_id)),
          )
        : previousShyfts;
    set({
      profile: nextProfile,
      shyfts: isFollowingFeed && !hasAnyFollows ? [] : nextShyfts,
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
      set({ profile, shyfts: previousShyfts });
    }
  },

  toggleFollowTeam: async (teamId, currentlyFollowed) => {
    const profile = get().profile;
    if (!profile) return;
    const previousShyfts = get().shyfts;
    const nextTeams = currentlyFollowed
      ? profile.follows.teams.filter((id) => id !== teamId)
      : [...profile.follows.teams, teamId];
    const nextProfile = { ...profile, follows: { ...profile.follows, teams: nextTeams } };
    const isFollowingFeed = get().filters.feed === 'following';
    const hasAnyFollows = nextProfile.follows.players.length > 0 || nextProfile.follows.teams.length > 0;
    const nextShyfts =
      isFollowingFeed && currentlyFollowed
        ? previousShyfts.filter(
            (signal) =>
              !isShyft(signal) ||
              signal.team_id !== teamId ||
              (signal.subject_type === 'player' && nextProfile.follows.players.includes(signal.player_id ?? -1)),
          )
        : previousShyfts;
    set({
      profile: nextProfile,
      shyfts: isFollowingFeed && !hasAnyFollows ? [] : nextShyfts,
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
      set({ profile, shyfts: previousShyfts });
    }
  },

  updatePreferences: async (payload) => {
    const profile = get().profile;
    if (!profile) return;
    const preferences = await api.updatePreferences(payload);
    set({ profile: { ...profile, preferences } });
  },

}));
