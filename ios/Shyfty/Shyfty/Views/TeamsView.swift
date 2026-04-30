import SwiftUI

struct TeamsView: View {
    @EnvironmentObject private var auth: AuthViewModel
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
            .toolbar { accountToolbar }
            .sheet(isPresented: $auth.showAuthSheet) {
                AuthView()
                    .environmentObject(auth)
            }
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
            LazyVStack(spacing: 10) {
                ForEach(filteredTeams) { team in
                    NavigationLink(value: team) {
                        teamRow(team)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func teamRow(_ team: Team) -> some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(team.name)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.ink)
                    .lineLimit(1)
                Text("\(team.leagueName) · \(team.playerCount) players")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }
            Spacer()
            if let count = team.signalCount, count > 0 {
                Text("\(count)")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(ShyftyTheme.accent)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(ShyftyTheme.accentSoft)
                    .clipShape(Capsule())
            }
            Image(systemName: "chevron.right")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(ShyftyTheme.muted.opacity(0.55))
        }
        .padding(16)
        .shyftyPanel(strong: true)
    }

    @ToolbarContentBuilder
    private var accountToolbar: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            if let user = auth.currentUser {
                NavigationLink {
                    AccountView()
                } label: {
                    Text(user.email)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.muted)
                        .lineLimit(1)
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
