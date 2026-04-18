import Charts
import SwiftUI

struct PlayerDetailView: View {
    let playerID: Int

    @State private var player: Player?
    @State private var signals: [Signal] = []
    @State private var metrics: [MetricSeriesPoint] = []
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                if let player {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(player.leagueName.uppercased())
                            .font(.caption)
                            .foregroundStyle(.blue)
                        Text(player.name)
                            .font(.largeTitle.bold())
                        Text("\(player.teamName) · \(player.position)")
                            .foregroundStyle(.secondary)
                    }
                }

                if let metricKey = metrics.first?.metrics.keys.sorted().first {
                    Chart(metrics, id: \.gameDate) { point in
                        if let value = point.metrics[metricKey] {
                            LineMark(
                                x: .value("Game", point.gameDate),
                                y: .value(metricKey, value)
                            )
                            .interpolationMethod(.catmullRom)
                            .foregroundStyle(.blue)
                        }
                    }
                    .frame(height: 240)
                    .padding()
                    .background(Color.white.opacity(0.05))
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                }

                VStack(spacing: 12) {
                    ForEach(signals) { signal in
                        SignalCardView(signal: signal)
                    }
                }

                if let errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                }
            }
            .padding()
        }
        .navigationTitle("Player Detail")
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

            player = try await playerRequest
            signals = try await signalRequest
            metrics = try await metricRequest
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

