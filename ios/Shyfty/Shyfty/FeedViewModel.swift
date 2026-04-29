import Foundation

enum FeedMode: String, Equatable {
    case all = "all"
    case following = "following"
}

@MainActor
final class FeedViewModel: ObservableObject {
    @Published var signals: [Signal] = []
    @Published var selectedLeague: String = "ALL"
    @Published var selectedType: String = "ALL"
    @Published var feedMode: FeedMode = .all
    @Published var isLoading = false
    @Published var isLoadingMore = false
    @Published var hasMore = false
    @Published var nextCursor: Int? = nil
    @Published var errorMessage: String?
    @Published var profile: UserProfile?

    var freshness: FreshnessContext? {
        signals.first?.freshness
    }

    var groupedSignals: [GroupedSignal] {
        var seen: [String: Int] = [:]
        var keys: [String] = []
        var groups: [[Signal]] = []

        for signal in signals {
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

        return zip(keys, groups).map { key, sigs in
            GroupedSignal(id: key, signals: sigs.sorted { $0.importance > $1.importance })
        }
    }

    func loadSignals() async {
        isLoading = true
        errorMessage = nil
        hasMore = false
        nextCursor = nil
        do {
            let page = try await APIClient.shared.fetchSignals(
                league: selectedLeague == "ALL" ? nil : selectedLeague,
                signalType: selectedType == "ALL" ? nil : selectedType,
                feed: feedMode == .following ? "following" : nil
            )
            signals = page.items
            hasMore = page.hasMore
            nextCursor = page.nextCursor
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func loadMore() async {
        guard hasMore, !isLoadingMore, let cursor = nextCursor else { return }
        isLoadingMore = true
        do {
            let page = try await APIClient.shared.fetchSignals(
                league: selectedLeague == "ALL" ? nil : selectedLeague,
                signalType: selectedType == "ALL" ? nil : selectedType,
                feed: feedMode == .following ? "following" : nil,
                cursor: cursor
            )
            signals += page.items
            hasMore = page.hasMore
            nextCursor = page.nextCursor
        } catch { }
        isLoadingMore = false
    }

    func loadProfile() async {
        do {
            profile = try await APIClient.shared.fetchProfile()
        } catch {
            profile = nil
        }
    }

    func isFollowed(signal: Signal) -> Bool {
        guard let profile else { return false }
        if let playerID = signal.playerID {
            return profile.follows.players.contains(playerID)
        }
        return profile.follows.teams.contains(signal.teamID)
    }

    func toggleFollow(for signal: Signal) async {
        guard let profile else { return }
        if let playerID = signal.playerID {
            await toggleFollowPlayer(id: playerID, profile: profile)
        } else {
            await toggleFollowTeam(id: signal.teamID, profile: profile)
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
            savedViews: profile.savedViews
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
            savedViews: profile.savedViews
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
        let previous = signals
        do {
            if signals.first(where: { $0.id == signalId })?.userReaction == type {
                try await APIClient.shared.clearReaction(signalId: signalId)
            } else {
                try await APIClient.shared.setReaction(signalId: signalId, type: type)
            }
            await loadSignals()
        } catch {
            signals = previous
            errorMessage = error.localizedDescription
        }
    }

    func toggleFavorite(signalId: Int) async {
        guard let signal = signals.first(where: { $0.id == signalId }) else { return }
        do {
            if signal.isFavorited {
                try await APIClient.shared.removeFavorite(signalId: signalId)
            } else {
                try await APIClient.shared.addFavorite(signalId: signalId)
            }
            await loadSignals()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
