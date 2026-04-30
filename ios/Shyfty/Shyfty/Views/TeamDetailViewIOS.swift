import SwiftUI

struct TeamDetailViewIOS: View {
    let teamID: Int

    @EnvironmentObject private var auth: AuthViewModel
    @State private var team: TeamDetail?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ZStack {
            ShyftyBackground()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
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
                    } else if let team {
                        header(team)
                        recentSignals(team)
                        roster(team)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
            }
        }
        .navigationDestination(for: Int.self) { playerID in
            PlayerDetailView(playerID: playerID)
        }
        .navigationTitle("Team")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task { await load() }
    }

    private func header(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(team.leagueName.uppercased())
                .shyftyEyebrow()
            Text(team.name)
                .shyftyHeadline(34)
            Text("\(team.playerCount) players · \(team.recentSignals.count) recent signals")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
        .padding(20)
        .shyftyPanel()
    }

    private func recentSignals(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent Signals")
                .shyftyEyebrow()
                .padding(.horizontal, 6)
            if team.recentSignals.isEmpty {
                Text("No recent signals are active for this team yet.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .shyftyPanel(strong: true)
            } else {
                ForEach(team.recentSignals) { signal in
                    SignalCardView(signal: signal)
                }
            }
        }
    }

    private func roster(_ team: TeamDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Players")
                .shyftyEyebrow()
                .padding(.horizontal, 6)
            ForEach(team.players) { player in
                NavigationLink(value: player.id) {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(player.name)
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.ink)
                            Text(player.position)
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                        }
                        Spacer()
                        Image(systemName: "chevron.right")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(ShyftyTheme.muted.opacity(0.55))
                    }
                    .padding(16)
                    .shyftyPanel(strong: true)
                }
                .buttonStyle(.plain)
            }
        }
    }

    @MainActor
    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            team = try await APIClient.shared.fetchTeam(id: teamID)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
