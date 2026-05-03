import SwiftUI

struct PlayersView: View {
    @State private var players: [Player] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var query = ""

    private var filteredPlayers: [Player] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return players }
        return players.filter {
            $0.name.lowercased().contains(q) || $0.teamName.lowercased().contains(q) || $0.leagueName.lowercased().contains(q)
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        header
                        searchField
                        content
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                }
            }
            .navigationDestination(for: Int.self) { playerID in
                PlayerDetailView(playerID: playerID)
            }
            .navigationTitle("Players")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .task { await load() }
            .refreshable { await load() }
        }
        .preferredColorScheme(.dark)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Players")
                .shyftyHeadline(30)
            Text("Browse player signal context by name, team, or league.")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .padding(20)
        .shyftyPanel()
    }

    private var searchField: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(ShyftyTheme.muted)
            TextField("Search players", text: $query)
                .foregroundStyle(ShyftyTheme.ink)
                .tint(ShyftyTheme.accent)
                .autocorrectionDisabled()
        }
        .shyftyField()
    }

    private let columns = [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)]

    @ViewBuilder
    private var content: some View {
        if isLoading {
            ProgressView()
                .tint(ShyftyTheme.accent)
                .frame(maxWidth: .infinity, minHeight: 180)
                .shyftyPanel(strong: true)
        } else if let errorMessage {
            Text(errorMessage)
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.danger)
                .padding(18)
                .frame(maxWidth: .infinity, alignment: .leading)
                .shyftyPanel(strong: true)
        } else {
            LazyVGrid(columns: columns, spacing: 10) {
                ForEach(filteredPlayers) { player in
                    NavigationLink(value: player.id) {
                        playerCell(player)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func playerCell(_ player: Player) -> some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(player.name)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.ink)
                    .lineLimit(1)

                HStack(spacing: 5) {
                    Text("\(player.teamName) · \(player.position)")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                        .lineLimit(1)
                    if let count = player.signalCount, count > 0 {
                        Text("•")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Color.white.opacity(0.2))
                        Text("\(count) signal\(count == 1 ? "" : "s")")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundStyle(ShyftyTheme.muted)
                            .lineLimit(1)
                    }
                }
            }
            Spacer(minLength: 0)
            ZStack {
                Circle()
                    .fill(Color.white.opacity(0.03))
                    .overlay(
                        Circle()
                            .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)
                    )
                Image(systemName: "chevron.right")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.muted)
            }
            .frame(width: 26, height: 26)
        }
        .padding(.horizontal, 13)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .shyftyPanel(strong: true)
    }

    @MainActor
    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            players = try await APIClient.shared.fetchPlayers()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
