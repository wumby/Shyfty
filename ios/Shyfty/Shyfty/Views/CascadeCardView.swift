import SwiftUI

struct CascadeCardView: View {
    let cascade: CascadeSignal
    var isFollowed: Bool? = nil
    var onFollowToggle: (() -> Void)? = nil

    private let accent = Color(red: 0.38, green: 0.78, blue: 1.0)

    var body: some View {
        NavigationLink(value: cascade) {
            VStack(alignment: .leading, spacing: 14) {
                header
                Text(cascade.narrativeSummary ?? "→ Usage redistributed")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.ink)
                    .fixedSize(horizontal: false, vertical: true)
                contributors
            }
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(ShyftyTheme.panelStrong)
                    .overlay(
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .strokeBorder(accent.opacity(0.34), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "arrow.triangle.branch")
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(accent)
                .frame(width: 32, height: 32)
                .background(accent.opacity(0.14))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 4) {
                Text(cascade.trigger.player.name)
                    .font(.system(size: 22, weight: .semibold, design: .serif))
                    .foregroundStyle(ShyftyTheme.ink)
                    .lineLimit(1)
                Text("Minutes DROP")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(ShyftyTheme.danger)
                Text("\(cascade.team) • \(SignalFormatting.eventDateText(cascade.gameDate))")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }

            Spacer()
        }
    }

    private var contributors: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(cascade.contributors.prefix(3), id: \.signalID) { contributor in
                HStack(spacing: 8) {
                    Text(contributor.player.name)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.ink)
                        .lineLimit(1)
                    Spacer()
                    Text("\(formatDelta(contributor.delta)) \(shortMetric(contributor.stat))")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(ShyftyTheme.success)
                }
            }
            if cascade.contributors.count > 3 {
                Text("+\(cascade.contributors.count - 3) more")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.muted)
            }
        }
    }

    private func formatDelta(_ value: Double) -> String {
        let rounded = value.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(value)) : String(format: "%.1f", value)
        return "\(value >= 0 ? "+" : "")\(rounded)"
    }

    private func shortMetric(_ metric: String) -> String {
        switch metric {
        case "points": return "pts"
        case "rebounds": return "reb"
        case "assists": return "ast"
        case "minutes_played", "minutes": return "min"
        case "usage_rate": return "usage"
        default: return SignalFormatting.metricLabel(metric).lowercased()
        }
    }
}
