import SwiftUI

struct FeedView: View {
    @StateObject private var viewModel = FeedViewModel()
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    private let leagues = ["ALL", "NBA", "NFL"]
    private let signalTypes = ["ALL", "SPIKE", "DROP", "SHIFT", "CONSISTENCY", "OUTLIER"]

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                ScrollView {
                    VStack(spacing: 16) {
                        headerView

                        if horizontalSizeClass == .regular {
                            HStack(alignment: .top, spacing: 14) {
                                filtersPanel
                                    .frame(width: 240)
                                feedBody
                            }
                        } else {
                            filtersPanel
                            feedBody
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                }
            }
            .navigationDestination(for: Int.self) { playerID in
                PlayerDetailView(playerID: playerID)
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Text("Shyfty")
                        .font(.system(size: 20, weight: .semibold, design: .serif))
                        .foregroundStyle(ShyftyTheme.ink)
                }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    NavigationLink {
                        FavoritesView()
                    } label: {
                        Image(systemName: "star")
                            .foregroundStyle(ShyftyTheme.muted)
                    }

                    if auth.currentUser != nil {
                        NavigationLink {
                            AccountView()
                        } label: {
                            Image(systemName: "person.crop.circle")
                                .foregroundStyle(ShyftyTheme.muted)
                        }
                    } else {
                        Button("Sign In") {
                            auth.isSignUp = false
                            auth.showAuthSheet = true
                        }
                        .foregroundStyle(ShyftyTheme.muted)
                    }
                }
            }
            .toolbarBackground(.hidden, for: .navigationBar)
            .task {
                await viewModel.loadSignals()
            }
            .onChange(of: viewModel.selectedLeague) { _, _ in
                Task { await viewModel.loadSignals() }
            }
            .onChange(of: viewModel.selectedType) { _, _ in
                Task { await viewModel.loadSignals() }
            }
            .sheet(isPresented: $auth.showAuthSheet) {
                AuthView()
                    .environmentObject(auth)
            }
        }
        .preferredColorScheme(.dark)
    }

    private var headerView: some View {
        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 8) {
                    ShyftyAccentDot()
                    Text("Signal intelligence")
                        .shyftyEyebrow()
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Shyfty")
                        .font(.system(size: 11, weight: .semibold))
                        .tracking(4.0)
                        .foregroundStyle(Color(red: 1.0, green: 0.85, blue: 0.74))
                        .textCase(.uppercase)
                    Text("Editorial live board for player volatility and role shifts.")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                        .lineSpacing(2)
                }
            }

            Text("Read the board, not just the box score.")
                .shyftyHeadline(30)
        }
        .padding(20)
        .shyftyPanel()
    }

    private var feedBody: some View {
        VStack(alignment: .leading, spacing: 14) {
            if viewModel.isLoading {
                VStack(spacing: 14) {
                    ProgressView()
                        .tint(ShyftyTheme.accent)
                    Text("Refreshing signal feed")
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
                    .background(ShyftyTheme.danger.opacity(0.12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .strokeBorder(ShyftyTheme.danger.opacity(0.22), lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
            } else if viewModel.signals.isEmpty {
                VStack(spacing: 10) {
                    Text("No signals in this view")
                        .shyftyHeadline(24)
                    Text("Try widening the league or signal type filters.")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                }
                .frame(maxWidth: .infinity, minHeight: 220)
                .shyftyPanel(strong: true)
            } else {
                HStack {
                    Text("\(viewModel.signals.count) signals")
                        .font(.system(size: 11, weight: .semibold))
                        .tracking(1.8)
                        .foregroundStyle(ShyftyTheme.muted)
                        .textCase(.uppercase)
                    Spacer()
                }
                .padding(.horizontal, 6)

                LazyVStack(spacing: 12) {
                    ForEach(viewModel.signals) { signal in
                        NavigationLink(value: signal.playerID) {
                            SignalCardView(signal: signal)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(12)
        .shyftyPanel(strong: true)
    }

    private var filtersPanel: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 8) {
                ShyftyAccentDot()
                Text("Filters")
                    .shyftyEyebrow()
            }

            Text("Keep the board trimmed without burying the controls.")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
                .lineSpacing(2)

            FilterChipsView(title: "League", options: leagues, selection: $viewModel.selectedLeague)
            FilterChipsView(title: "Signal Type", options: signalTypes, selection: $viewModel.selectedType)
        }
        .padding(18)
        .background {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(ShyftyTheme.panel)
                .overlay(
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .strokeBorder(ShyftyTheme.border, lineWidth: 1)
                )
                .overlay(alignment: .center) {
                    gridOverlay
                        .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
                }
        }
    }

    private var gridOverlay: some View {
        GeometryReader { geometry in
            Path { path in
                let step: CGFloat = 34
                var x: CGFloat = 0
                while x <= geometry.size.width {
                    path.move(to: CGPoint(x: x, y: 0))
                    path.addLine(to: CGPoint(x: x, y: geometry.size.height))
                    x += step
                }

                var y: CGFloat = 0
                while y <= geometry.size.height {
                    path.move(to: CGPoint(x: 0, y: y))
                    path.addLine(to: CGPoint(x: geometry.size.width, y: y))
                    y += step
                }
            }
            .stroke(ShyftyTheme.muted.opacity(0.08), lineWidth: 1)
        }
    }
}
