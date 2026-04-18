import Foundation

@MainActor
final class FeedViewModel: ObservableObject {
    @Published var signals: [Signal] = []
    @Published var selectedLeague: String = "ALL"
    @Published var selectedType: String = "ALL"
    @Published var isLoading = false
    @Published var errorMessage: String?

    func loadSignals() async {
        isLoading = true
        errorMessage = nil
        do {
            signals = try await APIClient.shared.fetchSignals(
                league: selectedLeague == "ALL" ? nil : selectedLeague,
                signalType: selectedType == "ALL" ? nil : selectedType
            )
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func setReaction(on signalId: Int, type: String) async {
        let previous = signals
        do {
            if signals.first(where: { $0.id == signalId })?.userReaction == type {
                try await APIClient.shared.clearReaction(signalId: signalId)
            } else {
                try await APIClient.shared.setReaction(signalId: signalId, type: type)
            }
            await loadSignals()
        } catch {
            signals = previous
            errorMessage = error.localizedDescription
        }
    }

    func toggleFavorite(signalId: Int) async {
        guard let signal = signals.first(where: { $0.id == signalId }) else { return }
        do {
            if signal.isFavorited {
                try await APIClient.shared.removeFavorite(signalId: signalId)
            } else {
                try await APIClient.shared.addFavorite(signalId: signalId)
            }
            await loadSignals()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
