import SwiftUI

struct CascadeDetailView: View {
    let cascade: CascadeSignal

    var body: some View {
        ZStack {
            ShyftyBackground()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(cascade.trigger.player.name)
                            .shyftyHeadline(30)
                        Text("Minutes DROP → Usage redistributed")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(ShyftyTheme.accent)
                        Text("\(cascade.team) • \(SignalFormatting.eventDateText(cascade.gameDate))")
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(ShyftyTheme.muted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(18)
                    .shyftyPanel(strong: true)

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Contributors")
                            .shyftyEyebrow()
                        ForEach(cascade.contributors, id: \.signalID) { contributor in
                            HStack {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(contributor.player.name)
                                        .font(.system(size: 16, weight: .semibold))
                                        .foregroundStyle(ShyftyTheme.ink)
                                    Text(contributor.metricLabel)
                                        .font(.system(size: 12, weight: .medium))
                                        .foregroundStyle(ShyftyTheme.muted)
                                }
                                Spacer()
                                Text(formatDelta(contributor.delta))
                                    .font(.system(size: 18, weight: .bold))
                                    .foregroundStyle(ShyftyTheme.success)
                            }
                            .padding(.vertical, 8)
                        }
                    }
                    .padding(18)
                    .shyftyPanel(strong: true)

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Underlying Signals")
                            .shyftyEyebrow()
                        ForEach(cascade.underlyingSignals) { signal in
                            NavigationLink(value: signal) {
                                SignalListRowView(signal: signal)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(18)
                    .shyftyPanel(strong: true)
                }
                .padding(14)
            }
        }
        .navigationTitle("Cascade")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func formatDelta(_ value: Double) -> String {
        let rounded = value.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(value)) : String(format: "%.1f", value)
        return "\(value >= 0 ? "+" : "")\(rounded)"
    }
}
