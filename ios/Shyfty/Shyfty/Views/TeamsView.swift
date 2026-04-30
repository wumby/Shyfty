import SwiftUI

struct TeamsView: View {
    @State private var teams: [Team] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var query = ""

    private var filteredTeams: [Team] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return teams }
        return teams.filter {
            $0.name.lowercased().contains(q) || $0.leagueName.lowercased().contains(q)
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
            .navigationDestination(for: Team.self) { team in
                TeamDetailViewIOS(teamID: team.id)
            }
            .navigationDestination(for: Int.self) { playerID in
                PlayerDetailView(playerID: playerID)
            }
            .navigationTitle("Teams")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .task { await load() }
            .refreshable { await load() }
        }
        .preferredColorScheme(.dark)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Teams")
                .shyftyHeadline(30)
            Text("Scan teams and jump into their active signal context.")
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
            TextField("Search teams", text: $query)
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
                ForEach(filteredTeams) { team in
                    NavigationLink(value: team) {
                        teamCell(team)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func teamCell(_ team: Team) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(team.name)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.ink)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                Text(team.leagueName)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }
            HStack {
                if let count = team.signalCount, count > 0 {
                    Text("\(count)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(ShyftyTheme.accent)
                        .padding(.horizontal, 7)
                        .padding(.vertical, 3)
                        .background(ShyftyTheme.accentSoft)
                        .clipShape(Capsule())
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.muted.opacity(0.5))
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .shyftyPanel(strong: true)
    }

    @MainActor
    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            teams = try await APIClient.shared.fetchTeams()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
