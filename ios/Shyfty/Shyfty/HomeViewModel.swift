import Foundation

@MainActor
final class HomeViewModel: ObservableObject {
    @Published var signals: [Signal] = []
    @Published var trendingSignals: [Signal] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    var featuredSignal: Signal? {
        trendingSignals.first ?? signals.first
    }

    var topSignals: [Signal] {
        Array((trendingSignals.isEmpty ? signals : trendingSignals).dropFirst().prefix(2))
    }

    var totalCountLabel: String {
        "\(signals.count)"
    }

    var nbaCountLabel: String {
        "\(signals.filter { $0.leagueName == "NBA" }.count)"
    }

    var highImpactLabel: String {
        "\(signals.filter { SignalFormatting.importance(for: $0.importance) == "High" }.count)"
    }

    func load() async {
        isLoading = true
        errorMessage = nil

        do {
            async let signalRequest = APIClient.shared.fetchSignals()
            async let trendingRequest = APIClient.shared.fetchTrendingSignals()

            signals = try await signalRequest.items
            trendingSignals = try await trendingRequest
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}
