import Foundation

enum FeedMode: String, Equatable {
    case all = "all"
    case following = "following"
}

enum FeedDisplayItem: Identifiable {
    case signalGroup(GroupedSignal)
    case cascade(CascadeSignal)

    var id: String {
        switch self {
        case .signalGroup(let group): return "group-\(group.id)"
        case .cascade(let cascade): return cascade.id
        }
    }
}

@MainActor
final class FeedViewModel: ObservableObject {
    @Published var feedItems: [FeedItem] = []
    @Published var selectedLeague: String = "ALL"
    @Published var selectedType: String = "ALL"
    @Published var feedMode: FeedMode = .all
    @Published var isLoading = false
    @Published var isLoadingMore = false
    @Published var hasMore = false
    @Published var nextCursor: Int? = nil
    @Published var errorMessage: String?
    @Published var profile: UserProfile?
    private var lastLoadMoreCursor: Int?

    init(initialFeedMode: FeedMode = .all) {
        self.feedMode = initialFeedMode
    }

    var signals: [Signal] {
        feedItems.flatMap { item in
            switch item {
            case .signal(let signal):
                return [signal]
            case .cascade(let cascade):
                return cascade.underlyingSignals
            }
        }
    }

    var groupedFeedItems: [FeedDisplayItem] {
        var seen: [String: Int] = [:]
        var keys: [String] = []
        var groups: [[Signal]] = []
        var displayItems: [FeedDisplayItem] = []

        for item in feedItems {
            if case .cascade(let cascade) = item {
                displayItems.append(.cascade(cascade))
                continue
            }

            guard case .signal(let signal) = item else { continue }
            let key: String
            if let pid = signal.playerID {
                key = "p\(pid)_\(signal.eventDate)"
            } else {
                key = "t\(signal.teamID)_\(signal.eventDate)"
            }
            if let idx = seen[key] {
                groups[idx].append(signal)
            } else {
                seen[key] = groups.count
                keys.append(key)
                groups.append([signal])
            }
        }

        displayItems += zip(keys, groups).map { key, sigs in
            GroupedSignal(id: key, signals: sigs.sorted { $0.importance > $1.importance })
        }.map(FeedDisplayItem.signalGroup)
        return displayItems
    }

    var groupedSignals: [GroupedSignal] {
        groupedFeedItems.compactMap {
            if case .signalGroup(let group) = $0 { return group }
            return nil
        }
    }

    func loadSignals() async {
        isLoading = true
        errorMessage = nil
        hasMore = false
        nextCursor = nil
        lastLoadMoreCursor = nil
        do {
            let page = try await APIClient.shared.fetchSignals(
                league: selectedLeague == "ALL" ? nil : selectedLeague,
                signalType: selectedType == "ALL" ? nil : selectedType,
                feed: feedMode == .following ? "following" : nil
            )
            feedItems = page.items
            hasMore = page.hasMore
            nextCursor = page.nextCursor
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func loadMore() async {
        guard hasMore, !isLoadingMore, let cursor = nextCursor else { return }
        guard lastLoadMoreCursor != cursor else { return }
        isLoadingMore = true
        lastLoadMoreCursor = cursor
        do {
            let page = try await APIClient.shared.fetchSignals(
                league: selectedLeague == "ALL" ? nil : selectedLeague,
                signalType: selectedType == "ALL" ? nil : selectedType,
                feed: feedMode == .following ? "following" : nil,
                cursor: cursor
            )
            let existingIDs = Set(feedItems.map(\.id))
            let newItems = page.items.filter { !existingIDs.contains($0.id) }
            feedItems += newItems
            hasMore = page.hasMore
            nextCursor = page.nextCursor
        } catch {
            errorMessage = error.localizedDescription
            lastLoadMoreCursor = nil
        }
        isLoadingMore = false
    }

    func loadProfile() async {
        do {
            profile = try await APIClient.shared.fetchProfile()
        } catch {
            profile = nil
        }
    }

    func applySignalEngagementChange(_ notification: Notification) {
        guard let signalId = notification.userInfo?["signalId"] as? Int else { return }
        let reactionSummary = notification.userInfo?["reactionSummary"] as? ReactionSummary
        let rawUserReaction = notification.userInfo?["userReaction"]
        let userReaction = rawUserReaction is NSNull ? nil : rawUserReaction as? String
        let commentCount = notification.userInfo?["commentCount"] as? Int
        let sourceSignal = signals.first { $0.id == signalId }

        feedItems = feedItems.map { item in
            switch item {
            case .signal(let signal):
                return .signal(patchSignal(signal, id: signalId, sourceSignal: sourceSignal, reactionSummary: reactionSummary, userReaction: userReaction, commentCount: commentCount))
            case .cascade(let cascade):
                let signals = cascade.underlyingSignals.map {
                    patchSignal($0, id: signalId, sourceSignal: sourceSignal, reactionSummary: reactionSummary, userReaction: userReaction, commentCount: commentCount)
                }
                return .cascade(CascadeSignal(
                    id: cascade.id,
                    gameID: cascade.gameID,
                    teamID: cascade.teamID,
                    team: cascade.team,
                    leagueName: cascade.leagueName,
                    gameDate: cascade.gameDate,
                    createdAt: cascade.createdAt,
                    trigger: cascade.trigger,
                    contributors: cascade.contributors,
                    underlyingSignals: signals,
                    narrativeSummary: cascade.narrativeSummary
                ))
            }
        }
    }

    private func patchSignal(_ signal: Signal, id: Int, sourceSignal: Signal?, reactionSummary: ReactionSummary?, userReaction: String?, commentCount: Int?) -> Signal {
        let isExactSignal = signal.id == id
        let isSameCommentGroup = sourceSignal.map { signal.isInSameDisplayGroup(as: $0) } ?? isExactSignal
        guard isExactSignal || (commentCount != nil && isSameCommentGroup) else { return signal }
        var next = signal
        if isExactSignal, let reactionSummary {
            next = next.withReaction(reactionSummary: reactionSummary, userReaction: userReaction)
        }
        if isSameCommentGroup, let commentCount {
            next = next.withCommentCount(commentCount)
        }
        return next
    }

    func isFollowed(signal: Signal) -> Bool {
        guard let profile else { return false }
        if let playerID = signal.playerID {
            return profile.follows.players.contains(playerID)
        }
        return profile.follows.teams.contains(signal.teamID)
    }

    func isFollowed(cascade: CascadeSignal) -> Bool {
        guard let profile else { return false }
        if let playerID = cascade.trigger.player.id {
            return profile.follows.players.contains(playerID)
        }
        return profile.follows.teams.contains(cascade.teamID)
    }

    func toggleFollow(for signal: Signal) async {
        guard let profile else { return }
        if let playerID = signal.playerID {
            await toggleFollowPlayer(id: playerID, profile: profile)
        } else {
            await toggleFollowTeam(id: signal.teamID, profile: profile)
        }
    }

    func toggleFollow(for cascade: CascadeSignal) async {
        guard let profile else { return }
        if let playerID = cascade.trigger.player.id {
            await toggleFollowPlayer(id: playerID, profile: profile)
        } else {
            await toggleFollowTeam(id: cascade.teamID, profile: profile)
        }
    }

    private func toggleFollowPlayer(id: Int, profile: UserProfile) async {
        let wasFollowed = profile.follows.players.contains(id)
        let nextPlayers = wasFollowed
            ? profile.follows.players.filter { $0 != id }
            : profile.follows.players + [id]
        self.profile = UserProfile(
            preferences: profile.preferences,
            follows: UserProfile.Follows(players: nextPlayers, teams: profile.follows.teams)
        )
        do {
            if wasFollowed {
                try await APIClient.shared.unfollowPlayer(id: id)
            } else {
                try await APIClient.shared.followPlayer(id: id)
            }
        } catch {
            self.profile = profile
        }
    }

    private func toggleFollowTeam(id: Int, profile: UserProfile) async {
        let wasFollowed = profile.follows.teams.contains(id)
        let nextTeams = wasFollowed
            ? profile.follows.teams.filter { $0 != id }
            : profile.follows.teams + [id]
        self.profile = UserProfile(
            preferences: profile.preferences,
            follows: UserProfile.Follows(players: profile.follows.players, teams: nextTeams)
        )
        do {
            if wasFollowed {
                try await APIClient.shared.unfollowTeam(id: id)
            } else {
                try await APIClient.shared.followTeam(id: id)
            }
        } catch {
            self.profile = profile
        }
    }

    func setReaction(on signalId: Int, type: String) async {
        let previous = feedItems
        do {
            if signals.first(where: { $0.id == signalId })?.userReaction == type {
                try await APIClient.shared.clearReaction(signalId: signalId)
            } else {
                try await APIClient.shared.setReaction(signalId: signalId, type: type)
            }
            await loadSignals()
        } catch {
            feedItems = previous
            errorMessage = error.localizedDescription
        }
    }

}
