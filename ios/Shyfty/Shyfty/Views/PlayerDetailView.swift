import Charts
import SwiftUI

struct PlayerDetailView: View {
    let playerID: Int

    @EnvironmentObject private var auth: AuthViewModel
    @State private var player: Player?
    @State private var isFollowed = false
    @State private var signals: [Signal] = []
    @State private var metrics: [MetricSeriesPoint] = []
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

                    if let metricKey = metrics.first?.metrics.keys.sorted().first {
                        VStack(alignment: .leading, spacing: 14) {
                            Text(metricKey.replacingOccurrences(of: "_", with: " ").capitalized)
                                .shyftyEyebrow()
                            Chart(metrics, id: \.gameDate) { point in
                                if let value = point.metrics[metricKey] {
                                    AreaMark(
                                        x: .value("Game", point.gameDate),
                                        y: .value(metricKey, value)
                                    )
                                    .interpolationMethod(.catmullRom)
                                    .foregroundStyle(
                                        LinearGradient(
                                            colors: [ShyftyTheme.accent.opacity(0.32), ShyftyTheme.accent.opacity(0.02)],
                                            startPoint: .top,
                                            endPoint: .bottom
                                        )
                                    )

                                    LineMark(
                                        x: .value("Game", point.gameDate),
                                        y: .value(metricKey, value)
                                    )
                                    .interpolationMethod(.catmullRom)
                                    .foregroundStyle(ShyftyTheme.accent)
                                    .lineStyle(.init(lineWidth: 3))
                                }
                            }
                            .chartXAxis(.hidden)
                            .chartYAxis {
                                AxisMarks(position: .leading) {
                                    AxisGridLine(stroke: .init(lineWidth: 0.5))
                                        .foregroundStyle(ShyftyTheme.border)
                                    AxisValueLabel()
                                        .foregroundStyle(ShyftyTheme.muted)
                                }
                            }
                            .frame(height: 240)
                        }
                        .padding(20)
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
                ForEach(rows) { row in
                    HStack(alignment: .center, spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("\(row.homeAway == "Away" ? "@" : "vs") \(row.opponent)")
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.ink)
                                .lineLimit(1)
                            Text("\(SignalFormatting.eventDateText(row.gameDate))\(row.season.map { " · \($0)" } ?? "")")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                                .lineLimit(1)
                        }
                        .frame(width: 112, alignment: .leading)

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(playerStats(row), id: \.label) { stat in
                                    boxScoreCell(label: stat.label, value: stat.value)
                                }
                            }
                        }
                    }
                    .padding(12)
                    .shyftyPanel(strong: true)
                }
            }
        }
    }

    private func boxScoreCell(label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 9, weight: .semibold))
                .tracking(1.1)
                .foregroundStyle(ShyftyTheme.muted)
            Text(value)
                .font(.system(size: 14, weight: .semibold, design: .monospaced))
                .foregroundStyle(ShyftyTheme.ink)
        }
        .frame(width: 66, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.white.opacity(0.035))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private func playerStats(_ row: PlayerBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendInt(&stats, "PTS", row.points)
        appendInt(&stats, "REB", row.rebounds)
        appendInt(&stats, "AST", row.assists)
        appendDouble(&stats, "MIN", row.minutesPlayed)
        appendPercent(&stats, "USG", row.usageRate)
        appendInt(&stats, "STL", row.steals)
        appendInt(&stats, "BLK", row.blocks)
        appendInt(&stats, "TO", row.turnovers)
        appendInt(&stats, "+/-", row.plusMinus)
        appendPercent(&stats, "FG%", row.fgPct)
        appendPercent(&stats, "3P%", row.fg3Pct)
        appendPercent(&stats, "FT%", row.ftPct)
        appendInt(&stats, "PASS YDS", row.passingYards)
        appendInt(&stats, "RUSH YDS", row.rushingYards)
        appendInt(&stats, "REC YDS", row.receivingYards)
        appendInt(&stats, "TD", row.touchdowns)
        return stats.map { (label: $0.0, value: $0.1) }
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
            async let playerRequest = APIClient.shared.fetchPlayer(id: playerID)
            async let signalRequest = APIClient.shared.fetchPlayerSignals(id: playerID)
            async let metricRequest = APIClient.shared.fetchPlayerMetrics(id: playerID)

            let loadedPlayer = try await playerRequest
            player = loadedPlayer
            isFollowed = loadedPlayer.isFollowed
            signals = try await signalRequest
            metrics = try await metricRequest
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
}
