import SwiftUI

struct SignalsView: View {
    @StateObject private var viewModel = FeedViewModel()
    @EnvironmentObject private var auth: AuthViewModel
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
            .navigationDestination(for: Signal.self) { signal in
                SignalDetailView(signalId: signal.id, signal: signal)
            }
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
                if viewModel.feedMode == .all {
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
            }
            .task {
                await viewModel.loadProfile()
                await viewModel.loadSignals()
            }
            .refreshable {
                await viewModel.loadProfile()
                await viewModel.loadSignals()
            }
            .sheet(isPresented: $showFilters) {
                SignalFilterSheetView(viewModel: viewModel)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
            .sheet(isPresented: $auth.showAuthSheet) {
                AuthView()
                    .environmentObject(auth)
            }
        }
        .preferredColorScheme(.dark)
    }

    private var headerBar: some View {
        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Signals")
                    .shyftyHeadline(28)
                Text("Standout performances from recent games.")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }

            HStack(spacing: 0) {
                tabButton("For You", mode: .all)
                tabButton("Following", mode: .following)
            }
            .padding(3)
            .background(Color.white.opacity(0.03))
            .overlay(
                Capsule()
                    .strokeBorder(ShyftyTheme.border, lineWidth: 1)
            )
            .clipShape(Capsule())
        }
        .padding(18)
        .shyftyPanel()
    }

    private func tabButton(_ title: String, mode: FeedMode) -> some View {
        Button {
            guard viewModel.feedMode != mode else { return }
            viewModel.feedMode = mode
            Task { await viewModel.loadSignals() }
        } label: {
            Text(title)
                .font(.system(size: 12, weight: .semibold))
                .padding(.horizontal, 20)
                .padding(.vertical, 7)
                .background(viewModel.feedMode == mode ? Color.white.opacity(0.09) : Color.clear)
                .foregroundStyle(viewModel.feedMode == mode ? ShyftyTheme.ink : ShyftyTheme.muted)
                .clipShape(Capsule())
        }
    }

    private var signalContent: some View {
        VStack(alignment: .leading, spacing: 12) {
            if viewModel.isLoading {
                VStack(spacing: 12) {
                    ProgressView()
                        .tint(ShyftyTheme.accent)
                    Text("Loading signals")
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
                if viewModel.feedMode == .following {
                    followingEmptyState
                } else {
                    VStack(spacing: 10) {
                        Text("No signals in this view")
                            .shyftyHeadline(24)
                        Text("Widen the filters to reopen the board.")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(ShyftyTheme.muted)
                    }
                    .frame(maxWidth: .infinity, minHeight: 220)
                    .shyftyPanel(strong: true)
                }
            } else {
                VStack(spacing: 10) {
                    ForEach(viewModel.signals) { signal in
                        NavigationLink(value: signal) {
                            SignalListRowView(
                                signal: signal,
                                isFollowed: auth.currentUser != nil ? viewModel.isFollowed(signal: signal) : nil,
                                onFollowToggle: {
                                    guard auth.currentUser != nil else {
                                        auth.isSignUp = false
                                        auth.showAuthSheet = true
                                        return
                                    }
                                    Task { await viewModel.toggleFollow(for: signal) }
                                }
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var followingEmptyState: some View {
        if auth.currentUser == nil {
            VStack(spacing: 16) {
                Text("Sign in to build your Following feed.")
                    .shyftyHeadline(22)
                    .multilineTextAlignment(.center)
                Button {
                    auth.isSignUp = false
                    auth.showAuthSheet = true
                } label: {
                    Text("Sign In")
                        .font(.system(size: 12, weight: .semibold))
                        .tracking(1.8)
                        .textCase(.uppercase)
                        .padding(.horizontal, 28)
                        .padding(.vertical, 12)
                        .background(ShyftyTheme.accent)
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                }
            }
            .frame(maxWidth: .infinity, minHeight: 220)
            .shyftyPanel(strong: true)
        } else if let profile = viewModel.profile, profile.follows.players.isEmpty && profile.follows.teams.isEmpty {
            VStack(spacing: 14) {
                Text("Follow players or teams to build your feed.")
                    .shyftyHeadline(22)
                    .multilineTextAlignment(.center)
                HStack(spacing: 12) {
                    Text("Browse Signals")
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.horizontal, 18)
                        .padding(.vertical, 10)
                        .background(Color.white.opacity(0.05))
                        .foregroundStyle(ShyftyTheme.muted)
                        .overlay(Capsule().strokeBorder(ShyftyTheme.border, lineWidth: 1))
                        .clipShape(Capsule())
                        .onTapGesture {
                            viewModel.feedMode = .all
                            Task { await viewModel.loadSignals() }
                        }
                }
            }
            .frame(maxWidth: .infinity, minHeight: 220)
            .shyftyPanel(strong: true)
        } else {
            VStack(spacing: 10) {
                Text("No signals from your follows yet.")
                    .shyftyHeadline(22)
                    .multilineTextAlignment(.center)
                Text("Check back after the next game.")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }
            .frame(maxWidth: .infinity, minHeight: 220)
            .shyftyPanel(strong: true)
        }
    }
}
