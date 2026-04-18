import SwiftUI

enum ShyftyTab: Hashable {
    case home
    case signals
    case saved
    case profile
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

            SignalsView()
                .tabItem {
                    Label("Signals", systemImage: "waveform.path.ecg")
                }
                .tag(ShyftyTab.signals)

            NavigationStack {
                FavoritesView()
            }
            .tabItem {
                Label("Saved", systemImage: "star")
            }
            .tag(ShyftyTab.saved)

            NavigationStack {
                ProfileView()
            }
            .tabItem {
                Label("Profile", systemImage: "person")
            }
            .tag(ShyftyTab.profile)
        }
        .tint(ShyftyTheme.accent)
    }
}
