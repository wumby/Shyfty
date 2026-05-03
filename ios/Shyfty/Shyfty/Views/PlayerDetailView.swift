import SwiftUI

struct PlayerDetailView: View {
    let playerID: Int

    @EnvironmentObject private var auth: AuthViewModel
    @State private var player: Player?
    @State private var isFollowed = false
    @State private var signals: [Signal] = []
    @State private var errorMessage: String?

    private var signalGroups: [GroupedSignal] {
        var seen: [String: Int] = [:]
        var groups: [[Signal]] = []
        var keys: [String] = []
        for signal in signals {
            let key = signal.eventDate
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

                    if !signalGroups.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Signals")
                                .shyftyEyebrow()
                                .padding(.horizontal, 6)
                            ForEach(signalGroups) { group in
                                GroupedSignalCardView(signals: group.signals)
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
        .navigationDestination(for: Signal.self) { signal in
            SignalDetailView(signalId: signal.id, signal: signal)
        }
        .navigationTitle("Player Detail")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task {
            await load()
        }
        .onReceive(NotificationCenter.default.publisher(for: .signalEngagementDidChange)) { notification in
            applySignalEngagementChange(notification)
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
        VStack(alignment: .leading, spacing: 6) {
            Text("\(row.homeAway == "Away" ? "@" : "vs") \(compactTeamName(row.opponent)) • \(shortDate(row.gameDate))")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(ShyftyTheme.ink.opacity(0.9))
                .lineLimit(1)

            statLine(primaryStats(row), primary: true)
            if !secondaryStats(row).isEmpty {
                statLine(secondaryStats(row), primary: false)
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
                        .foregroundStyle(statColor(label: stat.label, value: stat.value, primary: primary))
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

    private func primaryStats(_ row: PlayerBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendInt(&stats, "PTS", row.points)
        appendInt(&stats, "REB", row.rebounds)
        appendInt(&stats, "AST", row.assists)
        appendDouble(&stats, "MIN", row.minutesPlayed)
        if let steals = row.steals, steals > 0 { stats.append(("STL", "\(steals)")) }
        if let blocks = row.blocks, blocks > 0 { stats.append(("BLK", "\(blocks)")) }
        appendInt(&stats, "TO", row.turnovers)
        appendInt(&stats, "PASS YDS", row.passingYards)
        appendInt(&stats, "RUSH YDS", row.rushingYards)
        appendInt(&stats, "REC YDS", row.receivingYards)
        appendInt(&stats, "TD", row.touchdowns)
        return stats
    }

    private func secondaryStats(_ row: PlayerBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendPercent(&stats, "FG%", row.fgPct)
        appendPercent(&stats, "3P%", row.fg3Pct)
        if let ftPct = row.ftPct, ftPct > 0 {
            appendPercent(&stats, "FT%", ftPct)
        }
        appendPercent(&stats, "USG", row.usageRate)
        if let plusMinus = row.plusMinus {
            let signed = plusMinus > 0 ? "+\(plusMinus)" : "\(plusMinus)"
            stats.append(("+/-", signed))
        }
        return stats
    }

    private func statColor(label: String, value: String, primary: Bool) -> Color {
        if label == "+/-" {
            if value.hasPrefix("-") { return ShyftyTheme.danger }
            if value.hasPrefix("+") || value != "0" { return ShyftyTheme.success }
        }
        return primary ? ShyftyTheme.ink : ShyftyTheme.muted.opacity(0.95)
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
        do {
            let loadedPlayer = try await APIClient.shared.fetchPlayer(id: playerID)
            player = loadedPlayer
            isFollowed = loadedPlayer.isFollowed
            signals = try await APIClient.shared.fetchPlayerSignals(id: playerID)
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

    private func applySignalEngagementChange(_ notification: Notification) {
        guard let signalId = notification.userInfo?["signalId"] as? Int else { return }
        let reactionSummary = notification.userInfo?["reactionSummary"] as? ReactionSummary
        let rawUserReaction = notification.userInfo?["userReaction"]
        let userReaction: ShyftReaction? = (rawUserReaction is NSNull) ? nil : (rawUserReaction as? String).flatMap(ShyftReaction.init(rawValue:))
        let commentCount = notification.userInfo?["commentCount"] as? Int
        let sourceSignal = signals.first { $0.id == signalId }

        signals = signals.map { signal in
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
    }
}
