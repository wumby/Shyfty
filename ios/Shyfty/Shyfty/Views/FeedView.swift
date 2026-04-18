import SwiftUI

struct FeedView: View {
    @StateObject private var viewModel = FeedViewModel()

    private let leagues = ["ALL", "NBA", "NFL"]
    private let signalTypes = ["ALL", "SPIKE", "DROP", "SHIFT", "CONSISTENCY", "OUTLIER"]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("LIVE SIGNALS")
                            .font(.caption.weight(.semibold))
                            .kerning(1.2)
                            .foregroundStyle(.cyan)
                        Text("Player movement, ranked for fast reading.")
                            .font(.largeTitle.bold())
                        Text("Short-form signal intelligence for NBA and NFL performance shifts.")
                            .foregroundStyle(.secondary)
                    }

                    FilterChipsView(title: "League", options: leagues, selection: $viewModel.selectedLeague)
                    FilterChipsView(title: "Signal Type", options: signalTypes, selection: $viewModel.selectedType)

                    if viewModel.isLoading {
                        VStack(spacing: 14) {
                            ProgressView()
                            Text("Refreshing signal feed")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, minHeight: 220)
                        .background(Color.white.opacity(0.04))
                        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
                    } else if let errorMessage = viewModel.errorMessage {
                        Text(errorMessage)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                            .background(Color.red.opacity(0.12))
                            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                    } else if viewModel.signals.isEmpty {
                        VStack(spacing: 10) {
                            Text("No signals in this view")
                                .font(.headline)
                            Text("Try widening the league or signal type filters.")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, minHeight: 220)
                        .background(Color.white.opacity(0.04))
                        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
                    } else {
                        HStack {
                            Text("\(viewModel.signals.count) signals")
                                .font(.footnote.weight(.medium))
                                .foregroundStyle(.secondary)
                            Spacer()
                        }

                        LazyVStack(spacing: 14) {
                            ForEach(viewModel.signals) { signal in
                                NavigationLink(value: signal.playerID) {
                                    SignalCardView(signal: signal)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
                .padding()
            }
            .background(
                LinearGradient(
                    colors: [Color.black, Color(red: 0.03, green: 0.06, blue: 0.12)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()
            )
            .navigationDestination(for: Int.self) { playerID in
                PlayerDetailView(playerID: playerID)
            }
            .navigationTitle("Signals")
            .toolbar {
                NavigationLink {
                    FavoritesView()
                } label: {
                    Image(systemName: "star")
                }
            }
            .task {
                await viewModel.loadSignals()
            }
            .onChange(of: viewModel.selectedLeague) { _, _ in
                Task { await viewModel.loadSignals() }
            }
            .onChange(of: viewModel.selectedType) { _, _ in
                Task { await viewModel.loadSignals() }
            }
        }
        .preferredColorScheme(.dark)
    }
}
