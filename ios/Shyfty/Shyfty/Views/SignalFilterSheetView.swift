import SwiftUI

struct SignalFilterSheetView: View {
    @ObservedObject var viewModel: FeedViewModel
    @Environment(\.dismiss) private var dismiss

    private let leagues = ["ALL", "NBA", "NFL"]
    private let signalTypes = ["ALL", "SPIKE", "DROP", "SHIFT", "CONSISTENCY", "OUTLIER"]

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Filters")
                                .shyftyHeadline(28)
                            Text("Keep browsing controls tucked away until you need them.")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                        }
                        .padding(18)
                        .shyftyPanel()

                        VStack(alignment: .leading, spacing: 16) {
                            FilterChipsView(title: "League", options: leagues, selection: $viewModel.selectedLeague)
                            FilterChipsView(title: "Signal Type", options: signalTypes, selection: $viewModel.selectedType)
                        }
                        .padding(18)
                        .shyftyPanel(strong: true)

                        Button {
                            viewModel.selectedLeague = "ALL"
                            viewModel.selectedType = "ALL"
                        } label: {
                            Text("Reset Filters")
                                .font(.system(size: 12, weight: .semibold))
                                .tracking(1.8)
                                .textCase(.uppercase)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(Color.white.opacity(0.04))
                                .foregroundStyle(ShyftyTheme.muted)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                                        .strokeBorder(ShyftyTheme.border, lineWidth: 1)
                                )
                                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close") { dismiss() }
                        .foregroundStyle(ShyftyTheme.muted)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Apply") {
                        Task {
                            await viewModel.loadSignals()
                            dismiss()
                        }
                    }
                    .foregroundStyle(Color(red: 1.0, green: 0.85, blue: 0.74))
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}
