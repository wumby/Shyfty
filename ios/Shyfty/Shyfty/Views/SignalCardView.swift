import SwiftUI

struct ShyftCardView: View {
    let shyft: Shyft

    private var tint: Color { ShyftFormatting.tint(for: shyft.shyftType) }
    private var importanceTone: Color {
        switch ShyftFormatting.importance(for: shyft.importance) {
        case "High":
            return ShyftyTheme.accent
        case "Medium":
            return ShyftyTheme.muted
        default:
            return ShyftyTheme.muted.opacity(0.75)
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            RoundedRectangle(cornerRadius: 2, style: .continuous)
                .fill(tint.opacity(ShyftFormatting.importance(for: shyft.importance) == "Watch" ? 0.35 : 0.8))
                .frame(width: 3)
                .padding(.vertical, 14)

            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top, spacing: 14) {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 8) {
                            Text(ShyftFormatting.signalLabel(shyft.shyftType).uppercased())
                                .font(.system(size: 10, weight: .semibold))
                                .kerning(1.6)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 6)
                                .foregroundStyle(tint)
                                .background(tint.opacity(0.12))
                                .overlay(
                                    Capsule()
                                        .strokeBorder(tint.opacity(0.22), lineWidth: 1)
                                )
                                .clipShape(Capsule())

                            Text(ShyftFormatting.importance(for: shyft.importance).uppercased())
                                .font(.system(size: 10, weight: .semibold))
                                .kerning(1.6)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 6)
                                .foregroundStyle(importanceTone == ShyftyTheme.accent ? Color(red: 1.0, green: 0.85, blue: 0.74) : importanceTone)
                                .background(importanceTone == ShyftyTheme.accent ? ShyftyTheme.accentSoft : Color.white.opacity(0.03))
                                .overlay(
                                    Capsule()
                                        .strokeBorder(importanceTone.opacity(0.3), lineWidth: 1)
                                )
                                .clipShape(Capsule())
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            Text(shyft.playerName)
                                .font(.system(size: 28, weight: .semibold, design: .serif))
                                .foregroundStyle(ShyftyTheme.ink)
                            Text(ShyftFormatting.signalSummary(for: shyft))
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(ShyftyTheme.ink)
                                .lineSpacing(2)
                            Text("\(shyft.teamName)  •  \(shyft.leagueName)  •  \(ShyftFormatting.eventDateText(shyft.eventDate))  •  Z \(shyft.zScore, specifier: "%.2f")  •  \(ShyftFormatting.relativeTime(from: shyft.createdAt))")
                                .font(.system(size: 11, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                            if shyft.commentCount > 0 {
                                Text("\(shyft.commentCount) discussing")
                                    .font(.system(size: 11, weight: .semibold))
                                    .foregroundStyle(ShyftyTheme.accent)
                            }
                        }
                    }

                    Spacer(minLength: 12)

                    VStack(alignment: .trailing, spacing: 6) {
                        Text(ShyftFormatting.metricLabel(for: shyft).uppercased())
                            .font(.system(size: 10, weight: .semibold))
                            .kerning(1.6)
                            .foregroundStyle(ShyftyTheme.muted)
                        Text(ShyftFormatting.deltaText(current: shyft.currentValue, baseline: shyft.baselineValue, movementPct: shyft.movementPct))
                            .font(.system(size: 28, weight: .semibold))
                            .foregroundStyle(tint)
                        Text("\(shyft.currentValue, specifier: "%.1f") / \(shyft.baselineValue, specifier: "%.1f")")
                            .font(.system(size: 11, weight: .medium, design: .monospaced))
                            .foregroundStyle(ShyftyTheme.muted)
                    }
                }

                Text(shyft.explanation)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted.opacity(0.9))
                    .lineSpacing(2)

                HStack(spacing: 12) {
                    metricPill(title: "Current", value: shyft.currentValue)
                    metricPill(title: "Baseline", value: shyft.baselineValue)
                }

                HStack {
                    Text(shyft.baselineWindow)
                    Spacer()
                    Text(ShyftFormatting.movementText(metricName: shyft.metricName, current: shyft.currentValue, baseline: shyft.baselineValue, movementPct: shyft.movementPct, metricLabel: shyft.metricLabel))
                        .foregroundStyle(ShyftyTheme.muted.opacity(0.85))
                }
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
            }
            .padding(.leading, 16)
            .padding(.trailing, 18)
            .padding(.vertical, 18)
        }
        .background(
            ShyftyTheme.cardGradient
        )
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .strokeBorder(ShyftyTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
    }

    private func metricPill(title: String, value: Double) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .semibold))
                .kerning(1.2)
                .foregroundStyle(ShyftyTheme.muted)
            Text("\(value, specifier: "%.1f")")
                .font(.system(size: 15, weight: .semibold, design: .monospaced))
                .foregroundStyle(ShyftyTheme.ink)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(Color.white.opacity(0.04))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(ShyftyTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}
