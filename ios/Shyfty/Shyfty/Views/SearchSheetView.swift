import SwiftUI

struct SearchSheetView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var auth: AuthViewModel

    @State private var query = ""
    @State private var players: [Player] = []
    @State private var isLoading = false
    @FocusState private var focused: Bool

    private var results: [Player] {
        let q = query.trimmingCharacters(in: .whitespaces).lowercased()
        guard q.count >= 2 else { return [] }
        return players.filter {
            $0.name.lowercased().contains(q) || $0.teamName.lowercased().contains(q)
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                VStack(spacing: 0) {
                    searchBar

                    if isLoading {
                        ProgressView()
                            .tint(ShyftyTheme.accent)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else if query.trimmingCharacters(in: .whitespaces).count < 2 {
                        emptyPrompt
                    } else if results.isEmpty {
                        noResults
                    } else {
                        ScrollView {
                            LazyVStack(spacing: 8) {
                                ForEach(results) { player in
                                    NavigationLink(value: player.id) {
                                        playerRow(player)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                            .padding(.horizontal, 14)
                            .padding(.vertical, 12)
                        }
                    }
                }
            }
            .navigationDestination(for: Int.self) { playerID in
                PlayerDetailView(playerID: playerID)
                    .environmentObject(auth)
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundStyle(ShyftyTheme.muted)
                }
            }
        }
        .preferredColorScheme(.dark)
        .task {
            guard players.isEmpty else { return }
            isLoading = true
            players = (try? await APIClient.shared.fetchPlayers()) ?? []
            isLoading = false
            focused = true
        }
    }

    private var searchBar: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
            TextField("Search players…", text: $query)
                .focused($focused)
                .foregroundStyle(ShyftyTheme.ink)
                .tint(ShyftyTheme.accent)
                .autocorrectionDisabled()
            if !query.isEmpty {
                Button { query = "" } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(ShyftyTheme.muted)
                        .font(.system(size: 14))
                }
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(ShyftyTheme.panelStrong)
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundStyle(ShyftyTheme.border),
            alignment: .bottom
        )
    }

    private var emptyPrompt: some View {
        VStack(spacing: 8) {
            Text("Search players")
                .shyftyHeadline(22)
            Text("Type a name or team to find a player.")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(20)
    }

    private var noResults: some View {
        VStack(spacing: 8) {
            Text("No results")
                .shyftyHeadline(22)
            Text("No players matched \"\(query.trimmingCharacters(in: .whitespaces))\"")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(20)
    }

    private func playerRow(_ player: Player) -> some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 3) {
                Text(player.name)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.ink)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                Text("\(player.teamName) · \(player.position) · \(player.leagueName)")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .lineLimit(1)
            }

            Spacer()

            if let count = player.shyftCount, count > 0 {
                Text("\(count)")
                    .font(.system(size: 11, weight: .semibold))
                    .tracking(0.5)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .foregroundStyle(ShyftyTheme.accent)
                    .background(ShyftyTheme.accentSoft)
                    .clipShape(Capsule())
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted.opacity(0.5))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .shyftyPanel(strong: true)
    }
}
