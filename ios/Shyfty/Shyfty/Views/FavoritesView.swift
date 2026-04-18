import SwiftUI

@MainActor
final class FavoritesViewModel: ObservableObject {
    @Published var signals: [Signal] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            signals = try await APIClient.shared.fetchFavorites()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct FavoritesView: View {
    @StateObject private var viewModel = FavoritesViewModel()

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        headerPanel
                        contentPanel
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                }
            }
            .navigationDestination(for: Signal.self) { signal in
                SignalDetailView(signalId: signal.id, signal: signal)
            }
            .navigationTitle("Saved")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Text("Saved")
                        .font(.system(size: 20, weight: .semibold, design: .serif))
                        .foregroundStyle(ShyftyTheme.ink)
                }
            }
            .task { await viewModel.load() }
            .refreshable { await viewModel.load() }
        }
        .preferredColorScheme(.dark)
    }

    private var headerPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: "star.fill")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.warning)
                Text("Saved Signals")
                    .shyftyEyebrow()
            }
            Text("Your starred signals")
                .shyftyHeadline(26)
            Text("\(viewModel.signals.count) saved")
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .padding(18)
        .shyftyPanel()
    }

    @ViewBuilder
    private var contentPanel: some View {
        if viewModel.isLoading {
            VStack(spacing: 12) {
                ProgressView().tint(ShyftyTheme.accent)
                Text("Loading saved signals…")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }
            .frame(maxWidth: .infinity, minHeight: 200)
            .shyftyPanel(strong: true)
        } else if let error = viewModel.errorMessage {
            Text(error)
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.danger)
                .padding(18)
                .shyftyPanel(strong: true)
        } else if viewModel.signals.isEmpty {
            VStack(spacing: 10) {
                Image(systemName: "star")
                    .font(.system(size: 30))
                    .foregroundStyle(ShyftyTheme.muted)
                Text("Nothing saved yet")
                    .shyftyHeadline(22)
                Text("Tap ★ on any signal to save it here.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity, minHeight: 200)
            .shyftyPanel(strong: true)
        } else {
            VStack(spacing: 10) {
                ForEach(viewModel.signals) { signal in
                    NavigationLink(value: signal) {
                        SignalListRowView(signal: signal)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}
