import SwiftUI

struct FavoritesView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "star.slash")
                .font(.system(size: 36))
                .foregroundStyle(.secondary)
            Text("Favorites stub")
                .font(.title3.weight(.semibold))
            Text("Pin favorite players here in the next iteration.")
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
        .background(Color.black)
        .navigationTitle("Favorites")
    }
}

