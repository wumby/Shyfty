import SwiftUI

struct GroupedSignalCardView: View {
    let signals: [Signal]
    var isFollowed: Bool? = nil
    var onFollowToggle: (() -> Void)? = nil

    private var sorted: [Signal] {
        signals.sorted { $0.importance > $1.importance }
    }

    var body: some View {
        if let primary = sorted.first {
            VStack(alignment: .leading, spacing: 0) {
                headerRow(primary)
                Color.white.opacity(0.06).frame(height: 1)
                signalRows
            }
            .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
            .shyftyPanel(strong: true)
        }
    }

    private func shortName(_ name: String) -> String {
        name.split(separator: " ").last.map(String.init) ?? name
    }

    private func matchupText(_ signal: Signal) -> Text {
        let muted = ShyftyTheme.muted
        let dot = Text(" · ").foregroundStyle(muted)

        // Team vs Opponent
        var base: Text
        if let opponent = signal.opponent, !opponent.isEmpty {
            let side = (signal.homeAway == "Away" || signal.homeAway == "@") ? "@" : "vs"
            base = Text("\(shortName(signal.teamName)) \(side) \(shortName(opponent))").foregroundStyle(muted)
        } else {
            base = Text(shortName(signal.teamName)).foregroundStyle(muted)
        }

        // W / L + score
        if let result = signal.gameResult, !result.isEmpty {
            let resultColor: Color = result == "W" ? ShyftyTheme.success : result == "L" ? ShyftyTheme.danger : muted
            base = base + dot + Text(result).foregroundStyle(resultColor)
            if let score = signal.finalScore, !score.isEmpty {
                let clean = score
                    .replacingOccurrences(of: " - ", with: "–")
                    .replacingOccurrences(of: "-", with: "–")
                base = base + Text(" \(clean)").foregroundStyle(muted)
            }
        }

        // Date — no year
        base = base + dot + Text(SignalFormatting.eventDateShort(signal.eventDate)).foregroundStyle(muted)
        return base
    }

    private func headerRow(_ signal: Signal) -> some View {
        let name = signal.subjectType == "team" ? signal.teamName : signal.playerName
        return HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                if let playerID = signal.playerID {
                    NavigationLink(value: playerID) {
                        Text(name)
                            .font(.system(size: 22, weight: .semibold, design: .serif))
                            .foregroundStyle(ShyftyTheme.ink)
                    }
                    .buttonStyle(.plain)
                } else {
                    Text(name)
                        .font(.system(size: 22, weight: .semibold, design: .serif))
                        .foregroundStyle(ShyftyTheme.ink)
                }
                matchupText(signal)
                    .font(.system(size: 12, weight: .medium))
            }

            Spacer()

            if let isFollowed, let onToggle = onFollowToggle {
                Button(action: onToggle) {
                    Text(isFollowed ? "✓ Following" : "+ Follow")
                        .font(.system(size: 9, weight: .semibold))
                        .tracking(1.5)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .foregroundStyle(isFollowed ? ShyftyTheme.accent : ShyftyTheme.muted)
                        .background(isFollowed ? ShyftyTheme.accentSoft : Color.white.opacity(0.04))
                        .overlay(Capsule().strokeBorder(isFollowed ? ShyftyTheme.accent.opacity(0.3) : ShyftyTheme.border, lineWidth: 1))
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
        .padding(16)
    }

    @ViewBuilder
    private var signalRows: some View {
        ForEach(Array(sorted.enumerated()), id: \.element.id) { index, signal in
            NavigationLink(value: signal) {
                signalRow(signal)
            }
            .buttonStyle(.plain)
            if index < sorted.count - 1 {
                Color.white.opacity(0.06).frame(height: 1)
            }
        }
    }

    private func signalRow(_ signal: Signal) -> some View {
        let tint = SignalFormatting.tint(for: signal.signalType)
        let delta = SignalFormatting.deltaText(current: signal.currentValue, baseline: signal.baselineValue, movementPct: signal.movementPct)
        let isUp = signal.trendDirection == "up"
        let isDown = signal.trendDirection == "down"
        let deltaTone: Color = isUp ? ShyftyTheme.success : isDown ? ShyftyTheme.danger : ShyftyTheme.muted
        let arrow = isUp ? "↑" : isDown ? "↓" : ""

        return HStack(alignment: .top, spacing: 14) {
            RoundedRectangle(cornerRadius: 2, style: .continuous)
                .fill(tint.opacity(0.82))
                .frame(width: 3)

            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    Text(SignalFormatting.metricLabel(for: signal))
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.ink)
                        .lineLimit(1)
                    Text(signal.signalType)
                        .font(.system(size: 9, weight: .bold))
                        .kerning(1.4)
                        .padding(.horizontal, 7)
                        .padding(.vertical, 4)
                        .foregroundStyle(tint)
                        .background(tint.opacity(0.12))
                        .overlay(Capsule().strokeBorder(tint.opacity(0.24), lineWidth: 1))
                        .clipShape(Capsule())
                }

                HStack(spacing: 6) {
                    Text(formatStat(signal.currentValue, metricName: signal.metricName))
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(ShyftyTheme.ink)
                    Text("/")
                        .font(.system(size: 16))
                        .foregroundStyle(ShyftyTheme.muted.opacity(0.5))
                    Text(formatStat(signal.baselineValue, metricName: signal.metricName))
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.muted)
                }
            }

            Spacer()

            HStack(alignment: .firstTextBaseline, spacing: 3) {
                Text(delta)
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(deltaTone)
                if !arrow.isEmpty {
                    Text(arrow)
                        .font(.system(size: 13))
                        .foregroundStyle(deltaTone)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
    }

    private func formatStat(_ value: Double, metricName: String) -> String {
        if metricName == "usage_rate" {
            let normalized = abs(value) <= 1 ? value * 100 : value
            return String(format: "%.1f%%", normalized)
        }
        return value.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(value)) : String(format: "%.1f", value)
    }
}
