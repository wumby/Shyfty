import SwiftUI

struct MainTabView: View {
    @State private var currentPage: Int = 0

    var body: some View {
        TabView(selection: $currentPage) {
            FeedView()
                .tag(0)
            PlayersView()
                .tag(1)
            TeamsView()
                .tag(2)
            AccountView()
                .tag(3)
        }
        .tabViewStyle(.page(indexDisplayMode: .never))
        .safeAreaInset(edge: .bottom, spacing: 0) {
            customTabBar
        }
        .preferredColorScheme(.dark)
    }

    private var customTabBar: some View {
        VStack(spacing: 0) {
            Rectangle()
                .fill(Color.white.opacity(0.07))
                .frame(height: 0.5)
            HStack(spacing: 0) {
                tabBarButton(icon: "house", label: "Home", page: 0)
                tabBarButton(icon: "person.2", label: "Players", page: 1)
                tabBarButton(icon: "shield", label: "Teams", page: 2)
                tabBarButton(icon: "person.crop.circle", label: "Account", page: 3)
            }
            .frame(height: 49)
            .background(.bar)
        }
        .background(.bar)
    }

    private func tabBarButton(icon: String, label: String, page: Int) -> some View {
        Button {
            withAnimation(.easeInOut(duration: 0.25)) {
                currentPage = page
            }
        } label: {
            VStack(spacing: 3) {
                Image(systemName: currentPage == page ? "\(icon).fill" : icon)
                    .font(.system(size: 22))
                    .foregroundStyle(currentPage == page ? ShyftyTheme.accent : ShyftyTheme.muted)
                Text(label)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(currentPage == page ? ShyftyTheme.accent : ShyftyTheme.muted)
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}
