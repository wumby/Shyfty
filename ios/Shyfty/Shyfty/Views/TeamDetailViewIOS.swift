import SwiftUI

struct TeamDetailViewIOS: View {
    let teamID: Int

    @EnvironmentObject private var auth: AuthViewModel
    @State private var team: TeamDetail?
    @State private var isLoading = false
    @State private var errorMessage: String?

    private func groupSignals(_ signals: [Signal]) -> [GroupedSignal] {
        var seen: [String: Int] = [:]
        var groups: [[Signal]] = []
        var keys: [String] = []
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

    var body: some View {
        ZStack {
            ShyftyBackground()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if isLoading {
                        ProgressView()
                            .tint(ShyftyTheme.accent)
                            .frame(maxWidth: .infinity, minHeight: 180)
                            .shyftyPanel(strong: true)
                    } else if let errorMessage {
                        Text(errorMessage)
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(ShyftyTheme.danger)
                            .padding(18)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .shyftyPanel(strong: true)
                    } else if let team {
                        header(team)
                        teamBoxScores(team.recentBoxScores)
                        recentSignals(team)
                        roster(team)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
            }
        }
        .navigationDestination(for: Int.self) { playerID in
            PlayerDetailView(playerID: playerID)
        }
        .navigationDestination(for: Signal.self) { signal in
            SignalDetailView(signalId: signal.id, signal: signal)
        }
        .navigationTitle("Team")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task { await load() }
        .onReceive(NotificationCenter.default.publisher(for: .signalEngagementDidChange)) { notification in
            applySignalEngagementChange(notification)
        }
    }

    private func header(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(team.leagueName.uppercased())
                .shyftyEyebrow()
            Text(team.name)
                .shyftyHeadline(34)
            Text("\(team.playerCount) players · \(team.recentSignals.count) recent signals")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .padding(20)
        .shyftyPanel()
    }

    private func recentSignals(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent Signals")
                .shyftyEyebrow()
                .padding(.horizontal, 6)
            if team.recentSignals.isEmpty {
                Text("No recent signals are active for this team yet.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .shyftyPanel(strong: true)
            } else {
                ForEach(groupSignals(team.recentSignals)) { group in
                    GroupedSignalCardView(signals: group.signals)
                }
            }
        }
    }

    private func roster(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Players")
                .shyftyEyebrow()
                .padding(.horizontal, 6)
            ForEach(team.players) { player in
                NavigationLink(value: player.id) {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(player.name)
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.ink)
                            Text(player.position)
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                        }
                        Spacer()
                        Image(systemName: "chevron.right")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(ShyftyTheme.muted.opacity(0.55))
                    }
                    .padding(16)
                    .shyftyPanel(strong: true)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func teamBoxScores(_ rows: [TeamBoxScore]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Last 5 Box Scores")
                .shyftyEyebrow()
                .padding(.horizontal, 6)

            if rows.isEmpty {
                Text("No team box scores are stored yet.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .shyftyPanel(strong: true)
            } else {
                VStack(spacing: 0) {
                    ForEach(Array(rows.enumerated()), id: \.element.id) { index, row in
                        compactTeamGameRow(row)
                        if index < rows.count - 1 {
                            Divider()
                                .overlay(Color.white.opacity(0.08))
                                .padding(.leading, 10)
                        }
                    }
                }
                .padding(.vertical, 4)
                .shyftyPanel(strong: true)
            }
        }
    }

    private func compactTeamGameRow(_ row: TeamBoxScore) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("\(row.homeAway == "Away" ? "@" : "vs") \(compactTeamName(row.opponent)) • \(shortDate(row.gameDate))")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(ShyftyTheme.ink.opacity(0.9))
                .lineLimit(1)

            statLine(primaryTeamStats(row), primary: true)
            if !secondaryTeamStats(row).isEmpty {
                statLine(secondaryTeamStats(row), primary: false)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .contentShape(Rectangle())
    }

    private func statLine(_ stats: [(label: String, value: String)], primary: Bool) -> some View {
        HStack(spacing: 6) {
            ForEach(Array(stats.enumerated()), id: \.offset) { index, stat in
                HStack(spacing: 3) {
                    Text(stat.label)
                        .font(.system(size: primary ? 10 : 9, weight: .semibold))
                        .foregroundStyle(primary ? ShyftyTheme.muted.opacity(0.9) : ShyftyTheme.muted.opacity(0.7))
                    Text(stat.value)
                        .font(.system(size: stat.label == "PTS" ? 13 : (primary ? 11 : 10), weight: stat.label == "PTS" ? .bold : .semibold, design: .monospaced))
                        .foregroundStyle(primary ? ShyftyTheme.ink : ShyftyTheme.muted.opacity(0.95))
                        .frame(minWidth: stat.label == "PTS" ? 24 : 20, alignment: .trailing)
                }
                if index < stats.count - 1 {
                    Text("•")
                        .font(.system(size: 9, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.muted.opacity(primary ? 0.5 : 0.35))
                }
            }
            Spacer(minLength: 0)
        }
        .lineLimit(1)
    }

    private func primaryTeamStats(_ row: TeamBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendInt(&stats, "PTS", row.points)
        appendInt(&stats, "REB", row.rebounds)
        appendInt(&stats, "AST", row.assists)
        appendInt(&stats, "TO", row.turnovers)
        appendDouble(&stats, "PACE", row.pace)
        appendDouble(&stats, "OFF RTG", row.offRating)
        return stats
    }

    private func secondaryTeamStats(_ row: TeamBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendPercent(&stats, "FG%", row.fgPct)
        appendPercent(&stats, "3P%", row.fg3Pct)
        return stats
    }

    private func compactTeamName(_ team: String) -> String {
        let words = team
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { !$0.isEmpty }
        guard words.count > 1 else { return team }
        let abbr = words.prefix(3).compactMap(\.first).map { String($0).uppercased() }.joined()
        return abbr.count >= 2 ? abbr : team
    }

    private func shortDate(_ isoDate: String) -> String {
        let parser = DateFormatter()
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.dateFormat = "yyyy-MM-dd"
        if let date = parser.date(from: isoDate) {
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.dateFormat = "MMM d"
            return formatter.string(from: date)
        }
        return SignalFormatting.eventDateText(isoDate)
    }

    private func appendInt(_ stats: inout [(String, String)], _ label: String, _ value: Int?) {
        if let value { stats.append((label, "\(value)")) }
    }

    private func appendDouble(_ stats: inout [(String, String)], _ label: String, _ value: Double?) {
        if let value { stats.append((label, value.truncatingRemainder(dividingBy: 1) == 0 ? "\(Int(value))" : String(format: "%.1f", value))) }
    }

    private func appendPercent(_ stats: inout [(String, String)], _ label: String, _ value: Double?) {
        guard let value else { return }
        let normalized = abs(value) <= 1 ? value * 100 : value
        stats.append((label, "\(normalized.truncatingRemainder(dividingBy: 1) == 0 ? "\(Int(normalized))" : String(format: "%.1f", normalized))%"))
    }

    @MainActor
    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            team = try await APIClient.shared.fetchTeam(id: teamID)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func applySignalEngagementChange(_ notification: Notification) {
        guard let team, let signalId = notification.userInfo?["signalId"] as? Int else { return }
        let reactionSummary = notification.userInfo?["reactionSummary"] as? ReactionSummary
        let rawUserReaction = notification.userInfo?["userReaction"]
        let userReaction: ShyftReaction? = (rawUserReaction is NSNull) ? nil : (rawUserReaction as? String).flatMap(ShyftReaction.init(rawValue:))
        let commentCount = notification.userInfo?["commentCount"] as? Int
        let sourceSignal = team.recentSignals.first { $0.id == signalId }

        let nextSignals = team.recentSignals.map { signal in
            let isExactSignal = signal.id == signalId
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

        self.team = TeamDetail(
            id: team.id,
            name: team.name,
            leagueName: team.leagueName,
            playerCount: team.playerCount,
            signalCount: team.signalCount,
            isFollowed: team.isFollowed,
            players: team.players,
            recentSignals: nextSignals,
            recentBoxScores: team.recentBoxScores
        )
    }
}
