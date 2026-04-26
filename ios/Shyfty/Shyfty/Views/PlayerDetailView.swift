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
                                            .background(isFollowed ? ShyftyTheme.accentSoft : ShyftyTheme.accentSoft)
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

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Signals")
                            .shyftyEyebrow()
                            .padding(.horizontal, 6)
                        ForEach(signals) { signal in
                            SignalCardView(signal: signal)
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
        .navigationTitle("Player Detail")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task {
            await load()
        }
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
