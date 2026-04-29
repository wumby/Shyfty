import SwiftUI

struct FeedView: View {
    @StateObject private var viewModel = FeedViewModel()
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    @State private var showFilterSheet = false
    @State private var showSearchSheet = false

    private let leagues = ["ALL", "NBA", "NFL"]
    private let signalTypes = ["ALL", "SPIKE", "DROP", "SHIFT", "OUTLIER"]

    private var hasActiveFilters: Bool {
        viewModel.selectedLeague != "ALL" || viewModel.selectedType != "ALL"
    }

    var body: some View {
        navigationRoot
            .preferredColorScheme(.dark)
    }

    private var navigationRoot: some View {
        NavigationStack {
            rootContent
                .navigationDestination(for: Int.self) { playerID in
                    PlayerDetailView(playerID: playerID)
                }
                .navigationDestination(for: Signal.self) { signal in
                    SignalDetailView(signalId: signal.id, signal: signal)
                }
                .navigationDestination(for: CascadeSignal.self) { cascade in
                    CascadeDetailView(cascade: cascade)
                }
                .navigationTitle("")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { toolbarContent }
                .toolbarBackground(.hidden, for: .navigationBar)
                .task {
                    await viewModel.loadSignals()
                    await viewModel.loadProfile()
                }
                .onChange(of: viewModel.selectedLeague) { _, _ in
                    Task { await viewModel.loadSignals() }
                }
                .onChange(of: viewModel.selectedType) { _, _ in
                    Task { await viewModel.loadSignals() }
                }
                .onChange(of: viewModel.feedMode) { _, _ in
                    Task { await viewModel.loadSignals() }
                }
                .sheet(isPresented: $auth.showAuthSheet) {
                    AuthView()
                        .environmentObject(auth)
                }
                .sheet(isPresented: $showFilterSheet) {
                    SignalFilterSheetView(viewModel: viewModel)
                        .presentationDetents([.medium, .large])
                }
                .sheet(isPresented: $showSearchSheet) {
                    SearchSheetView()
                        .environmentObject(auth)
                }
        }
    }

    private var rootContent: some View {
        ZStack {
            ShyftyBackground()
            ScrollView {
                mainStack
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
            }
        }
    }

    private var mainStack: some View {
        VStack(spacing: 16) {
            headerView
            if horizontalSizeClass == .regular {
                regularLayout
            } else {
                compactLayout
            }
        }
    }

    private var regularLayout: some View {
        HStack(alignment: .top, spacing: 14) {
            filtersPanel
                .frame(width: 240)
            VStack(spacing: 14) {
                feedModeSegment
                feedBody
            }
        }
    }

    private var compactLayout: some View {
        VStack(spacing: 16) {
            feedModeSegment
            feedBody
        }
    }

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .topBarLeading) {
            Text("Shyfty")
                .font(.system(size: 20, weight: .semibold, design: .serif))
                .foregroundStyle(ShyftyTheme.ink)
        }
        ToolbarItemGroup(placement: .topBarTrailing) {
            Button {
                showSearchSheet = true
            } label: {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(ShyftyTheme.muted)
            }

            if horizontalSizeClass != .regular {
                Button {
                    showFilterSheet = true
                } label: {
                    Image(systemName: "slider.horizontal.3")
                        .foregroundStyle(hasActiveFilters ? ShyftyTheme.accent : ShyftyTheme.muted)
                }
            }

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

    private var feedModeSegment: some View {
        HStack(spacing: 8) {
            Button("For You") { viewModel.feedMode = .all }
                .buttonStyle(ShyftyPillButtonStyle(active: viewModel.feedMode == .all))
            Button("Following") { viewModel.feedMode = .following }
                .buttonStyle(ShyftyPillButtonStyle(active: viewModel.feedMode == .following))
            Spacer()
        }
        .padding(.horizontal, 4)
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

    @ViewBuilder
    private var freshnessBanner: some View {
        if let f = viewModel.freshness, f.state != "live" {
            let isError = f.state == "error"
            HStack(spacing: 8) {
                Image(systemName: isError ? "exclamationmark.circle" : "clock")
                    .font(.system(size: 12, weight: .medium))
                Text(f.label)
                    .font(.system(size: 12, weight: .medium))
                Spacer()
                if let msg = f.delayedDataMessage {
                    Text(msg)
                        .font(.system(size: 11))
                        .lineLimit(1)
                }
            }
            .foregroundStyle(isError ? ShyftyTheme.danger : ShyftyTheme.warning)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background((isError ? ShyftyTheme.danger : ShyftyTheme.warning).opacity(0.10))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .strokeBorder((isError ? ShyftyTheme.danger : ShyftyTheme.warning).opacity(0.25), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
    }

    private var feedBody: some View {
        VStack(alignment: .leading, spacing: 14) {
            freshnessBanner

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
            } else if viewModel.feedMode == .following && viewModel.feedItems.isEmpty {
                VStack(spacing: 10) {
                    Text("Nothing here yet")
                        .shyftyHeadline(24)
                    Text("Follow players or teams to see their signals here.")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity, minHeight: 220)
                .shyftyPanel(strong: true)
            } else if viewModel.feedItems.isEmpty {
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
                let grouped = viewModel.groupedFeedItems
                HStack {
                    Text("\(grouped.count) \(grouped.count == 1 ? "story" : "stories")")
                        .font(.system(size: 11, weight: .semibold))
                        .tracking(1.8)
                        .foregroundStyle(ShyftyTheme.muted)
                        .textCase(.uppercase)
                    Spacer()
                }
                .padding(.horizontal, 6)

                LazyVStack(spacing: 12) {
                    ForEach(grouped) { item in
                        feedDisplayItemView(item)
                    }

                    if viewModel.hasMore {
                        Color.clear
                            .frame(height: 1)
                            .onAppear { Task { await viewModel.loadMore() } }
                    }
                    if viewModel.isLoadingMore {
                        ProgressView()
                            .tint(ShyftyTheme.accent)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                    }
                }
            }
        }
        .padding(12)
        .shyftyPanel(strong: true)
    }

    @ViewBuilder
    private func feedDisplayItemView(_ item: FeedDisplayItem) -> some View {
        switch item {
        case .cascade(let cascade):
            CascadeCardView(
                cascade: cascade,
                isFollowed: viewModel.isFollowed(cascade: cascade),
                onFollowToggle: { Task { await viewModel.toggleFollow(for: cascade) } }
            )
        case .signalGroup(let group):
            GroupedSignalCardView(
                signals: group.signals,
                isFollowed: viewModel.isFollowed(signal: group.primarySignal),
                onFollowToggle: { Task { await viewModel.toggleFollow(for: group.primarySignal) } }
            )
        }
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
