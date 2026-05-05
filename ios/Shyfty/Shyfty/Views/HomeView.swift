import SwiftUI

struct HomeView: View {
    @StateObject private var viewModel = HomeViewModel()
    @EnvironmentObject private var auth: AuthViewModel

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        introPanel
                        statRow
                        if let featuredSignal = viewModel.featuredSignal {
                            featuredModule(featuredSignal)
                        }
                        quickActions
                        if !viewModel.topSignals.isEmpty {
                            topSignalsModule
                        }
                        if let errorMessage = viewModel.errorMessage {
                            Text(errorMessage)
                                .font(.system(size: 13, weight: .medium))
                                .foregroundStyle(ShyftyTheme.danger)
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                }
            }
            .navigationDestination(for: Int.self) { playerID in
                PlayerDetailView(playerID: playerID)
            }
            .navigationTitle("Home")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Text("Shyfty")
                        .font(.system(size: 20, weight: .semibold, design: .serif))
                        .foregroundStyle(ShyftyTheme.ink)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    if let user = auth.currentUser {
                        NavigationLink {
                            AccountView()
                        } label: {
                            Text(user.email)
                                .font(.system(size: 13, weight: .semibold))
                                .lineLimit(1)
                        }
                        .foregroundStyle(ShyftyTheme.muted)
                    } else {
                        Button("Sign In") {
                            auth.isSignUp = false
                            auth.showAuthSheet = true
                        }
                        .foregroundStyle(ShyftyTheme.muted)
                    }
                }
            }
            .task {
                await viewModel.load()
            }
            .refreshable {
                await viewModel.load()
            }
            .sheet(isPresented: $auth.showAuthSheet) {
                AuthView()
                    .environmentObject(auth)
            }
        }
        .preferredColorScheme(.dark)
    }

    // Home is intentionally capped to a few overview modules instead of becoming the full product surface.
    private var introPanel: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 8) {
                ShyftyAccentDot()
                Text("Shyft intelligence")
                    .shyftyEyebrow()
            }
            Text("A calmer front page for tonight’s biggest movement.")
                .shyftyHeadline(30)
            Text("Use Home for the quick read. Jump into Players or Teams when you want roster-level context.")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
                .lineSpacing(2)
        }
        .padding(20)
        .shyftyPanel()
    }

    private var statRow: some View {
        HStack(spacing: 12) {
            overviewStat(title: "Live", value: viewModel.totalCountLabel, subtitle: "shyfts")
            overviewStat(title: "NBA", value: viewModel.nbaCountLabel, subtitle: "in feed")
            overviewStat(title: "High", value: viewModel.highImpactLabel, subtitle: "impact")
        }
    }

    private func overviewStat(title: String, value: String, subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .shyftyEyebrow()
            Text(value)
                .font(.system(size: 28, weight: .semibold, design: .serif))
                .foregroundStyle(ShyftyTheme.ink)
            Text(subtitle)
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .shyftyPanel(strong: true)
    }

    private func featuredModule(_ shyft: Shyft) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Featured Shyft")
                .shyftyEyebrow()
                .padding(.horizontal, 6)

            if let playerID = shyft.playerID {
                NavigationLink(value: playerID) {
                    CompactShyftCardView(shyft: shyft, emphasis: .featured)
                }
                .buttonStyle(.plain)
            } else {
                CompactShyftCardView(shyft: shyft, emphasis: .featured)
            }
        }
    }

    private var quickActions: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Shortcuts")
                .shyftyEyebrow()
                .padding(.horizontal, 6)

            HStack(spacing: 12) {
                shortcutButton(title: "Players", subtitle: "Browse roster", systemImage: "person.2")
                shortcutButton(title: "Teams", subtitle: "Browse clubs", systemImage: "shield")
            }
        }
    }

    private func shortcutButton(title: String, subtitle: String, systemImage: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(ShyftyTheme.accent)
                .frame(width: 34, height: 34)
                .background(ShyftyTheme.accentSoft)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.ink)
                Text(subtitle)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }

            Spacer()
        }
        .padding(16)
        .shyftyPanel(strong: true)
    }

    private var topSignalsModule: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Top Shyfts")
                .shyftyEyebrow()
                .padding(.horizontal, 6)

            VStack(spacing: 10) {
                ForEach(viewModel.topSignals) { shyft in
                    if let playerID = shyft.playerID {
                        NavigationLink(value: playerID) {
                            CompactShyftCardView(shyft: shyft, emphasis: .compact)
                        }
                        .buttonStyle(.plain)
                    } else {
                        CompactShyftCardView(shyft: shyft, emphasis: .compact)
                    }
                }
            }
        }
    }
}
