import SwiftUI

struct TeamDetailViewIOS: View {
    let teamID: Int

    @EnvironmentObject private var auth: AuthViewModel
    @State private var team: TeamDetail?
    @State private var isLoading = false
    @State private var errorMessage: String?

    private func groupShyfts(_ shyfts: [Shyft]) -> [GroupedShyft] {
        var seen: [String: Int] = [:]
        var groups: [[Shyft]] = []
        var keys: [String] = []
        for shyft in shyfts {
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
        return zip(keys, groups).map { key, sigs in
            GroupedShyft(id: key, shyfts: sigs.sorted { $0.importance > $1.importance })
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
                        recentShyfts(team)
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
        .navigationDestination(for: Shyft.self) { shyft in
            ShyftDetailView(shyftId: shyft.id, shyft: shyft)
        }
        .navigationTitle("Team")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task { await load() }
        .onReceive(NotificationCenter.default.publisher(for: .shyftEngagementDidChange)) { notification in
            applyShyftEngagementChange(notification)
        }
    }

    private func header(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(team.leagueName.uppercased())
                .shyftyEyebrow()
            Text(team.name)
                .shyftyHeadline(34)
            Text("\(team.playerCount) players · \(team.recentShyfts.count) recent shyfts")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .padding(20)
        .shyftyPanel()
    }

    private func recentShyfts(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent Shyfts")
                .shyftyEyebrow()
                .padding(.horizontal, 6)
            if team.recentShyfts.isEmpty {
                Text("No recent shyfts are active for this team yet.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .shyftyPanel(strong: true)
            } else {
                ForEach(groupShyfts(team.recentShyfts)) { group in
                    GroupedShyftCardView(shyfts: group.shyfts)
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
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("\(row.homeAway == "Away" ? "@" : "vs") \(row.opponent)")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.ink)
                        .lineLimit(1)
                    Text(shortDate(row.gameDate))
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                }
                Spacer()
                outcomeBadge(row)
            }

            statLine(primaryTeamStats(row), emphasized: true)
            if !secondaryTeamStats(row).isEmpty {
                statLine(secondaryTeamStats(row), emphasized: false)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 12)
        .padding(.vertical, 9)
        .contentShape(Rectangle())
    }

    private func statLine(_ stats: [(label: String, value: String)], emphasized: Bool) -> some View {
        HStack(spacing: 8) {
            ForEach(Array(stats.enumerated()), id: \.offset) { _, stat in
                VStack(alignment: .leading, spacing: 2) {
                    Text(stat.label)
                        .font(.system(size: emphasized ? 9 : 8, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.muted.opacity(emphasized ? 0.9 : 0.75))
                    Text(stat.value)
                        .font(.system(size: emphasized ? 13 : 12, weight: emphasized ? .semibold : .medium, design: .monospaced))
                        .foregroundStyle(ShyftyTheme.ink)
                }
                .frame(width: 58, alignment: .leading)
            }
            Spacer(minLength: 0)
        }
    }

    private func primaryTeamStats(_ row: TeamBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendInt(&stats, "PTS", row.points)
        appendInt(&stats, "REB", row.rebounds)
        appendInt(&stats, "AST", row.assists)
        appendInt(&stats, "TO", row.turnovers)
        return stats
    }

    private func secondaryTeamStats(_ row: TeamBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendPercent(&stats, "FG%", row.fgPct)
        appendPercent(&stats, "3P%", row.fg3Pct)
        return stats
    }

    private func outcomeBadge(_ row: TeamBoxScore) -> some View {
        let result = row.result ?? "—"
        let scoreText: String
        if let team = row.teamScore, let opponent = row.opponentScore {
            scoreText = "\(team)–\(opponent)"
        } else {
            scoreText = "—"
        }

        let tone: Color = result == "W" ? ShyftyTheme.success : result == "L" ? ShyftyTheme.danger : ShyftyTheme.muted
        return Text("\(result) \(scoreText)")
            .font(.system(size: 11, weight: .semibold, design: .monospaced))
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .foregroundStyle(tone)
            .background(tone.opacity(0.14))
            .overlay(Capsule().strokeBorder(tone.opacity(0.3), lineWidth: 1))
            .clipShape(Capsule())
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
        return ShyftFormatting.eventDateText(isoDate)
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

    private func applyShyftEngagementChange(_ notification: Notification) {
        guard let team, let shyftId = notification.userInfo?["shyftId"] as? Int else { return }
        let reactionSummary = notification.userInfo?["reactionSummary"] as? ReactionSummary
        let rawUserReaction = notification.userInfo?["userReaction"]
        let userReaction: ShyftReaction? = (rawUserReaction is NSNull) ? nil : (rawUserReaction as? String).flatMap(ShyftReaction.init(rawValue:))
        let commentCount = notification.userInfo?["commentCount"] as? Int
        let sourceSignal = team.recentShyfts.first { $0.id == shyftId }

        let nextSignals = team.recentShyfts.map { shyft in
            let isExactSignal = shyft.id == shyftId
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

        self.team = TeamDetail(
            id: team.id,
            name: team.name,
            leagueName: team.leagueName,
            playerCount: team.playerCount,
            shyftCount: team.shyftCount,
            isFollowed: team.isFollowed,
            players: team.players,
            recentShyfts: nextSignals,
            recentBoxScores: team.recentBoxScores
        )
    }
}
