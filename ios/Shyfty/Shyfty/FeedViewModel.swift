import Foundation

enum FeedMode: String, Equatable {
    case all = "all"
    case following = "following"
}

enum FeedDisplayItem: Identifiable {
    case shyftGroup(GroupedShyft)
    case cascade(CascadeShyft)

    var id: String {
        switch self {
        case .shyftGroup(let group): return "group-\(group.id)"
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

    var shyfts: [Shyft] {
        feedItems.flatMap { item in
            switch item {
            case .shyft(let shyft):
                return [shyft]
            case .cascade(let cascade):
                return cascade.underlyingShyfts
            }
        }
    }

    var groupedFeedItems: [FeedDisplayItem] {
        var seen: [String: Int] = [:]
        var keys: [String] = []
        var groups: [[Shyft]] = []
        var displayItems: [FeedDisplayItem] = []

        for item in feedItems {
            if case .cascade(let cascade) = item {
                displayItems.append(.cascade(cascade))
                continue
            }

            guard case .shyft(let shyft) = item else { continue }
            let key: String
            if let pid = shyft.playerID {
                key = "p\(pid)_\(shyft.eventDate)"
            } else {
                key = "t\(shyft.teamID)_\(shyft.eventDate)"
            }
            if let idx = seen[key] {
                groups[idx].append(shyft)
            } else {
                seen[key] = groups.count
                keys.append(key)
                groups.append([shyft])
            }
        }

        displayItems += zip(keys, groups).map { key, sigs in
            GroupedShyft(id: key, shyfts: sigs.sorted { $0.importance > $1.importance })
        }.map(FeedDisplayItem.shyftGroup)
        return displayItems
    }

    var groupedShyfts: [GroupedShyft] {
        groupedFeedItems.compactMap {
            if case .shyftGroup(let group) = $0 { return group }
            return nil
        }
    }

    func loadShyfts() async {
        isLoading = true
        errorMessage = nil
        hasMore = false
        nextCursor = nil
        lastLoadMoreCursor = nil
        do {
            let page = try await APIClient.shared.fetchShyfts(
                league: selectedLeague == "ALL" ? nil : selectedLeague,
                shyftType: selectedType == "ALL" ? nil : selectedType,
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
            let page = try await APIClient.shared.fetchShyfts(
                league: selectedLeague == "ALL" ? nil : selectedLeague,
                shyftType: selectedType == "ALL" ? nil : selectedType,
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

    func applyShyftEngagementChange(_ notification: Notification) {
        guard let shyftId = notification.userInfo?["shyftId"] as? Int else { return }
        let reactionSummary = notification.userInfo?["reactionSummary"] as? ReactionSummary
        let rawUserReaction = notification.userInfo?["userReaction"]
        let userReaction: ShyftReaction? = (rawUserReaction is NSNull) ? nil : (rawUserReaction as? String).flatMap(ShyftReaction.init(rawValue:))
        let commentCount = notification.userInfo?["commentCount"] as? Int
        let sourceSignal = shyfts.first { $0.id == shyftId }

        feedItems = feedItems.map { item in
            switch item {
            case .shyft(let shyft):
                return .shyft(patchShyft(shyft, id: shyftId, sourceSignal: sourceSignal, reactionSummary: reactionSummary, userReaction: userReaction, commentCount: commentCount))
            case .cascade(let cascade):
                let shyfts = cascade.underlyingShyfts.map {
                    patchShyft($0, id: shyftId, sourceSignal: sourceSignal, reactionSummary: reactionSummary, userReaction: userReaction, commentCount: commentCount)
                }
                return .cascade(CascadeShyft(
                    id: cascade.id,
                    gameID: cascade.gameID,
                    teamID: cascade.teamID,
                    team: cascade.team,
                    leagueName: cascade.leagueName,
                    gameDate: cascade.gameDate,
                    createdAt: cascade.createdAt,
                    trigger: cascade.trigger,
                    contributors: cascade.contributors,
                    underlyingShyfts: shyfts,
                    narrativeSummary: cascade.narrativeSummary
                ))
            }
        }
    }

    private func patchShyft(_ shyft: Shyft, id: Int, sourceSignal: Shyft?, reactionSummary: ReactionSummary?, userReaction: ShyftReaction?, commentCount: Int?) -> Shyft {
        let isExactSignal = shyft.id == id
        let isSameCommentGroup = sourceSignal.map { shyft.isInSameDisplayGroup(as: $0) } ?? isExactSignal
        guard isExactSignal || (commentCount != nil && isSameCommentGroup) else { return shyft }
        var next = shyft
        if isExactSignal, let reactionSummary {
            next = next.withReaction(reactionSummary: reactionSummary, userReaction: userReaction)
        }
        if isSameCommentGroup, let commentCount {
            next = next.withCommentCount(commentCount)
        }
        return next
    }

    func isFollowed(shyft: Shyft) -> Bool {
        guard let profile else { return false }
        if let playerID = shyft.playerID {
            return profile.follows.players.contains(playerID)
        }
        return profile.follows.teams.contains(shyft.teamID)
    }

    func isFollowed(cascade: CascadeShyft) -> Bool {
        guard let profile else { return false }
        if let playerID = cascade.trigger.player.id {
            return profile.follows.players.contains(playerID)
        }
        return profile.follows.teams.contains(cascade.teamID)
    }

    func toggleFollow(for shyft: Shyft) async {
        guard let profile else { return }
        if let playerID = shyft.playerID {
            await toggleFollowPlayer(id: playerID, profile: profile)
        } else {
            await toggleFollowTeam(id: shyft.teamID, profile: profile)
        }
    }

    func toggleFollow(for cascade: CascadeShyft) async {
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
            follows: UserProfile.Follows(players: nextPlayers, teams: profile.follows.teams),
            displayName: profile.displayName
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
            follows: UserProfile.Follows(players: profile.follows.players, teams: nextTeams),
            displayName: profile.displayName
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

    func setReaction(on shyftId: Int, type: ShyftReaction) async {
        let previous = feedItems
        do {
            if shyfts.first(where: { $0.id == shyftId })?.userReaction == type {
                try await APIClient.shared.clearReaction(shyftId: shyftId)
            } else {
                try await APIClient.shared.setReaction(shyftId: shyftId, type: type)
            }
            await loadShyfts()
        } catch {
            feedItems = previous
            errorMessage = error.localizedDescription
        }
    }

}
