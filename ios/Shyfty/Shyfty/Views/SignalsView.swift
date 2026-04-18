import SwiftUI

struct SignalsView: View {
    @StateObject private var viewModel = FeedViewModel()
    @State private var showFilters = false

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        headerBar
                        signalContent
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                }
            }
            // Navigate to signal detail by tapping a signal row
            .navigationDestination(for: Signal.self) { signal in
                SignalDetailView(signalId: signal.id, signal: signal)
            }
            // Navigate to player detail from links within detail views
            .navigationDestination(for: Int.self) { playerID in
                PlayerDetailView(playerID: playerID)
            }
            .navigationTitle("Signals")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Text("Signals")
                        .font(.system(size: 20, weight: .semibold, design: .serif))
                        .foregroundStyle(ShyftyTheme.ink)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showFilters = true
                    } label: {
                        Label("Filters", systemImage: "line.3.horizontal.decrease.circle")
                            .labelStyle(.iconOnly)
                            .foregroundStyle(ShyftyTheme.muted)
                    }
                }
            }
            .task {
                await viewModel.loadSignals()
            }
            .refreshable {
                await viewModel.loadSignals()
            }
            .sheet(isPresented: $showFilters) {
                SignalFilterSheetView(viewModel: viewModel)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
        }
        .preferredColorScheme(.dark)
    }

    private var headerBar: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                ShyftyAccentDot()
                Text("Board")
                    .shyftyEyebrow()
            }

            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Filtered live board")
                        .shyftyHeadline(28)
                    Text(filterSummary)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                }
                Spacer()
                Button {
                    showFilters = true
                } label: {
                    Text("Filters")
                        .font(.system(size: 11, weight: .semibold))
                        .tracking(1.8)
                        .textCase(.uppercase)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(ShyftyTheme.accentSoft)
                        .foregroundStyle(Color(red: 1.0, green: 0.85, blue: 0.74))
                        .overlay(
                            Capsule()
                                .strokeBorder(ShyftyTheme.accent.opacity(0.30), lineWidth: 1)
                        )
                        .clipShape(Capsule())
                }
            }
        }
        .padding(18)
        .shyftyPanel()
    }

    private var signalContent: some View {
        VStack(alignment: .leading, spacing: 12) {
            if viewModel.isLoading {
                VStack(spacing: 12) {
                    ProgressView()
                        .tint(ShyftyTheme.accent)
                    Text("Refreshing signal board")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                }
                .frame(maxWidth: .infinity, minHeight: 220)
                .shyftyPanel(strong: true)
            } else if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.danger)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(18)
                    .shyftyPanel(strong: true)
            } else if viewModel.signals.isEmpty {
                VStack(spacing: 10) {
                    Text("No signals in this view")
                        .shyftyHeadline(24)
                    Text("Widen the filters to reopen the board.")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                }
                .frame(maxWidth: .infinity, minHeight: 220)
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

    private var filterSummary: String {
        let league = viewModel.selectedLeague == "ALL" ? "All leagues" : viewModel.selectedLeague
        let type = viewModel.selectedType == "ALL" ? "All signals" : viewModel.selectedType.capitalized
        return "\(league) • \(type) • \(viewModel.signals.count) visible"
    }
}
