import SwiftUI

struct SignalCardView: View {
    let signal: Signal

    private var tint: Color { SignalFormatting.tint(for: signal.signalType) }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 8) {
                        Text(SignalFormatting.signalLabel(signal.signalType).uppercased())
                            .font(.caption.weight(.semibold))
                            .kerning(1.0)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(tint.opacity(0.16))
                            .overlay(
                                Capsule()
                                    .strokeBorder(tint.opacity(0.3), lineWidth: 1)
                            )
                            .clipShape(Capsule())

                        Text("\(SignalFormatting.importance(for: signal.importance)) IMPACT")
                            .font(.caption2.weight(.medium))
                            .kerning(0.8)
                            .foregroundStyle(.secondary)
                    }

                    Text(signal.playerName)
                        .font(.title3.weight(.semibold))
                    Text("\(signal.teamName) · \(signal.leagueName)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Spacer()
                VStack(alignment: .trailing, spacing: 6) {
                    Text(SignalFormatting.metricLabel(for: signal).uppercased())
                        .font(.caption2.weight(.medium))
                        .kerning(1.0)
                        .foregroundStyle(.secondary)
                    Text(SignalFormatting.deltaText(current: signal.currentValue, baseline: signal.baselineValue, movementPct: signal.movementPct))
                        .font(.title3.weight(.bold))
                    Text(SignalFormatting.movementText(metricName: signal.metricName, current: signal.currentValue, baseline: signal.baselineValue, movementPct: signal.movementPct, metricLabel: signal.metricLabel))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }

            Text(signal.explanation)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)

            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("CURRENT")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text("\(signal.currentValue, specifier: "%.1f")")
                        .font(.body.monospacedDigit().weight(.semibold))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.white.opacity(0.05))
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

                VStack(alignment: .leading, spacing: 6) {
                    Text("BASELINE")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text("\(signal.baselineValue, specifier: "%.1f")")
                        .font(.body.monospacedDigit().weight(.semibold))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.white.opacity(0.05))
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }

            HStack {
                Text(signal.baselineWindow)
                Spacer()
                Text(signal.eventDate, style: .date)
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            HStack {
                Text("z \(signal.zScore, specifier: "%.2f")")
                Spacer()
                Text(SignalFormatting.relativeTime(from: signal.createdAt))
            }
            .font(.caption.monospacedDigit())
            .foregroundStyle(.secondary)
        }
        .padding(18)
        .background(
            LinearGradient(
                colors: [Color.white.opacity(0.07), Color.white.opacity(0.04)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
    }
}
