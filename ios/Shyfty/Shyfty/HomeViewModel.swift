import Foundation

@MainActor
final class HomeViewModel: ObservableObject {
    @Published var shyfts: [Shyft] = []
    @Published var trendingShyfts: [Shyft] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    var featuredSignal: Shyft? {
        trendingShyfts.first ?? shyfts.first
    }

    var topSignals: [Shyft] {
        Array((trendingShyfts.isEmpty ? shyfts : trendingShyfts).dropFirst().prefix(2))
    }

    var totalCountLabel: String {
        "\(shyfts.count)"
    }

    var nbaCountLabel: String {
        "\(shyfts.filter { $0.leagueName == "NBA" }.count)"
    }

    var highImpactLabel: String {
        "\(shyfts.filter { ShyftFormatting.importance(for: $0.importance) == "High" }.count)"
    }

    func load() async {
        isLoading = true
        errorMessage = nil

        do {
            async let shyftRequest = APIClient.shared.fetchShyfts(feed: "for_you")
            async let trendingRequest = APIClient.shared.fetchTrendingShyfts()

            shyfts = try await shyftRequest.shyftItems
            trendingShyfts = try await trendingRequest
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}
