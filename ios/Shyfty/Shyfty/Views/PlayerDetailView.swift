import SwiftUI

struct PlayerDetailView: View {
    let playerID: Int

    @EnvironmentObject private var auth: AuthViewModel
    @State private var player: Player?
    @State private var isFollowed = false
    @State private var shyfts: [Shyft] = []
    @State private var errorMessage: String?

    private var shyftGroups: [GroupedShyft] {
        var seen: [String: Int] = [:]
        var groups: [[Shyft]] = []
        var keys: [String] = []
        for shyft in shyfts {
            let key = shyft.eventDate
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
                    if let player {
                        VStack(alignment: .leading, spacing: 10) {
                            HStack(alignment: .top) {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(player.leagueName.uppercased())
                                        .shyftyEyebrow()
                                        .foregroundStyle(Color(red: 1.0, green: 0.85, blue: 0.74))
                                    Text(player.name)
                                        .shyftyHeadline(36)
                                    Text("\(player.teamName) · \(player.position)")
                                        .font(.system(size: 14, weight: .medium))
                                        .foregroundStyle(ShyftyTheme.muted)
                                }
                                Spacer()
                                if auth.currentUser != nil {
                                    Button {
                                        Task { await toggleFollowPlayer() }
                                    } label: {
                                        Text(isFollowed ? "✓ Following" : "+ Follow")
                                            .font(.system(size: 10, weight: .semibold))
                                            .kerning(0.8)
                                            .padding(.horizontal, 12)
                                            .padding(.vertical, 8)
                                            .foregroundStyle(isFollowed ? ShyftyTheme.accent : Color(red: 1.0, green: 0.85, blue: 0.74))
                                            .background(ShyftyTheme.accentSoft)
                                            .overlay(
                                                Capsule()
                                                    .strokeBorder(ShyftyTheme.accent.opacity(isFollowed ? 0.35 : 0.25), lineWidth: 1)
                                            )
                                            .clipShape(Capsule())
                                    }
                                }
                            }
                        }
                        .padding(22)
                        .shyftyPanel()
                    }

                    if let boxScores = player?.recentBoxScores {
                        playerBoxScores(boxScores)
                    }

                    if !shyftGroups.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Shyfts")
                                .shyftyEyebrow()
                                .padding(.horizontal, 6)
                            ForEach(shyftGroups) { group in
                                GroupedShyftCardView(shyfts: group.shyfts)
                            }
                        }
                    }

                    if let errorMessage {
                        Text(errorMessage)
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(ShyftyTheme.danger)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
            }
        }
        .navigationDestination(for: Shyft.self) { shyft in
            ShyftDetailView(shyftId: shyft.id, shyft: shyft)
        }
        .navigationTitle("Player Detail")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task {
            await load()
        }
        .onReceive(NotificationCenter.default.publisher(for: .shyftEngagementDidChange)) { notification in
            applyShyftEngagementChange(notification)
        }
    }

    private func playerBoxScores(_ rows: [PlayerBoxScore]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Last 5 Box Scores")
                .shyftyEyebrow()
                .padding(.horizontal, 6)

            if rows.isEmpty {
                Text("No box scores are stored for this player yet.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .shyftyPanel(strong: true)
            } else {
                VStack(spacing: 0) {
                    ForEach(Array(rows.enumerated()), id: \.element.id) { index, row in
                        compactGameRow(row)
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

    private func compactGameRow(_ row: PlayerBoxScore) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("\(row.homeAway == "Away" ? "@" : "vs") \(row.opponent)")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.ink)
                    Text(shortDate(row.gameDate))
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                }
                Spacer()
                outcomeBadge(row)
            }

            statLine(primaryStats(row), emphasized: true)
            if !secondaryStats(row).isEmpty {
                statLine(secondaryStats(row), emphasized: false)
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
                        .foregroundStyle(statColor(label: stat.label, value: stat.value, primary: emphasized))
                }
                .frame(width: 58, alignment: .leading)
            }
            Spacer(minLength: 0)
        }
    }

    private func primaryStats(_ row: PlayerBoxScore) -> [(label: String, value: String)] {
        [
            ("PTS", intOrDash(row.points)),
            ("REB", intOrDash(row.rebounds)),
            ("AST", intOrDash(row.assists)),
            ("MIN", doubleOrDash(row.minutesPlayed)),
        ]
    }

    private func secondaryStats(_ row: PlayerBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = [
            ("FG%", percentOrDash(row.fgPct)),
            ("3P%", percentOrDash(row.fg3Pct)),
            ("+/-", plusMinusOrDash(row.plusMinus)),
            ("TO", intOrDash(row.turnovers)),
            ("STL", intOrDash(row.steals)),
            ("BLK", intOrDash(row.blocks)),
        ]
        if row.passingYards != nil || row.rushingYards != nil || row.receivingYards != nil || row.touchdowns != nil {
            stats.append(("PASS YDS", intOrDash(row.passingYards)))
            stats.append(("RUSH YDS", intOrDash(row.rushingYards)))
            stats.append(("REC YDS", intOrDash(row.receivingYards)))
            stats.append(("TD", intOrDash(row.touchdowns)))
        }
        return stats
    }

    private func statColor(label: String, value: String, primary: Bool) -> Color {
        if label == "+/-" {
            if value.hasPrefix("-") { return ShyftyTheme.danger }
            if value.hasPrefix("+") { return ShyftyTheme.success }
        }
        return primary ? ShyftyTheme.ink : ShyftyTheme.muted.opacity(0.95)
    }

    private func outcomeBadge(_ row: PlayerBoxScore) -> some View {
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

    private func intOrDash(_ value: Int?) -> String {
        guard let value else { return "—" }
        return "\(value)"
    }

    private func doubleOrDash(_ value: Double?) -> String {
        guard let value else { return "—" }
        return value.truncatingRemainder(dividingBy: 1) == 0 ? "\(Int(value))" : String(format: "%.1f", value)
    }

    private func percentOrDash(_ value: Double?) -> String {
        guard let value else { return "—" }
        let normalized = abs(value) <= 1 ? value * 100 : value
        return "\(normalized.truncatingRemainder(dividingBy: 1) == 0 ? "\(Int(normalized))" : String(format: "%.1f", normalized))%"
    }

    private func plusMinusOrDash(_ value: Int?) -> String {
        guard let value else { return "—" }
        return value > 0 ? "+\(value)" : "\(value)"
    }

    @MainActor
    private func load() async {
        do {
            let loadedPlayer = try await APIClient.shared.fetchPlayer(id: playerID)
            player = loadedPlayer
            isFollowed = loadedPlayer.isFollowed
            shyfts = try await APIClient.shared.fetchPlayerShyfts(id: playerID)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func toggleFollowPlayer() async {
        let wasFollowed = isFollowed
        isFollowed.toggle()
        do {
            if wasFollowed {
                try await APIClient.shared.unfollowPlayer(id: playerID)
            } else {
                try await APIClient.shared.followPlayer(id: playerID)
            }
        } catch {
            isFollowed = wasFollowed
        }
    }

    private func applyShyftEngagementChange(_ notification: Notification) {
        guard let shyftId = notification.userInfo?["shyftId"] as? Int else { return }
        let reactionSummary = notification.userInfo?["reactionSummary"] as? ReactionSummary
        let rawUserReaction = notification.userInfo?["userReaction"]
        let userReaction: ShyftReaction? = (rawUserReaction is NSNull) ? nil : (rawUserReaction as? String).flatMap(ShyftReaction.init(rawValue:))
        let commentCount = notification.userInfo?["commentCount"] as? Int
        let sourceSignal = shyfts.first { $0.id == shyftId }

        shyfts = shyfts.map { shyft in
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
    }
}
