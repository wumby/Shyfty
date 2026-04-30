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
                        recentSignals(team)
                        teamBoxScores(team.recentBoxScores)
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
                                ForEach(teamStats(row), id: \.label) { stat in
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
        .frame(width: 72, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.white.opacity(0.035))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private func teamStats(_ row: TeamBoxScore) -> [(label: String, value: String)] {
        var stats: [(String, String)] = []
        appendInt(&stats, "PTS", row.points)
        appendInt(&stats, "REB", row.rebounds)
        appendInt(&stats, "AST", row.assists)
        appendInt(&stats, "TO", row.turnovers)
        appendPercent(&stats, "FG%", row.fgPct)
        appendPercent(&stats, "3P%", row.fg3Pct)
        appendDouble(&stats, "PACE", row.pace)
        appendDouble(&stats, "OFF RTG", row.offRating)
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
        isLoading = true
        errorMessage = nil
        do {
            team = try await APIClient.shared.fetchTeam(id: teamID)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
