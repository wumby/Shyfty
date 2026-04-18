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
        // Optimistic update
        let previous = signals
        signals = signals.map { signal in
            guard signal.id == signalId else { return signal }
            // We can't mutate a let; just reload after API call for simplicity
            return signal
        }
        do {
            if signals.first(where: { $0.id == signalId })?.userReaction == type {
                try await APIClient.shared.clearReaction(signalId: signalId)
            } else {
                try await APIClient.shared.setReaction(signalId: signalId, type: type)
            }
            // Reload to get fresh counts
            await loadSignals()
        } catch {
            signals = previous
            errorMessage = error.localizedDescription
        }
    }
}
