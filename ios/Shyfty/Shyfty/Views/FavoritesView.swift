import SwiftUI

struct FavoritesView: View {
    var body: some View {
        ZStack {
            ShyftyBackground()

            VStack(spacing: 16) {
                Image(systemName: "star.slash")
                    .font(.system(size: 36))
                    .foregroundStyle(ShyftyTheme.muted)
                Text("Saved stub")
                    .shyftyHeadline(28)
                Text("Keep saved players and signals here in the next iteration.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(24)
            .shyftyPanel()
            .padding(14)
        }
        .navigationTitle("Saved")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
    }
}
