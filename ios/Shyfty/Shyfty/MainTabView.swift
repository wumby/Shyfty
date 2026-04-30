import SwiftUI

enum ShyftyTab: Hashable {
    case home
    case players
    case teams
}

struct MainTabView: View {
    @State private var selectedTab: ShyftyTab = .home

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView(selectedTab: $selectedTab)
                .tabItem {
                    Label("Home", systemImage: "house")
                }
                .tag(ShyftyTab.home)

            PlayersView()
                .tabItem {
                    Label("Players", systemImage: "person.2")
                }
                .tag(ShyftyTab.players)

            TeamsView()
                .tabItem {
                    Label("Teams", systemImage: "shield")
                }
                .tag(ShyftyTab.teams)
        }
        .tint(ShyftyTheme.accent)
    }
}
