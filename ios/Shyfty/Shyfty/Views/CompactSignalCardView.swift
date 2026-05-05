import SwiftUI

enum CompactSignalCardEmphasis {
    case compact
    case featured
}

struct CompactShyftCardView: View {
    let shyft: Shyft
    let emphasis: CompactSignalCardEmphasis

    private var tint: Color { ShyftFormatting.tint(for: shyft.shyftType) }

    var body: some View {
        VStack(alignment: .leading, spacing: emphasis == .featured ? 14 : 10) {
            HStack {
                Text(ShyftFormatting.signalLabel(shyft.shyftType).uppercased())
                    .font(.system(size: 10, weight: .semibold))
                    .kerning(1.5)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .foregroundStyle(tint)
                    .background(tint.opacity(0.12))
                    .overlay(
                        Capsule()
                            .strokeBorder(tint.opacity(0.24), lineWidth: 1)
                    )
                    .clipShape(Capsule())

                Spacer()

                Text(ShyftFormatting.deltaText(current: shyft.currentValue, baseline: shyft.baselineValue, movementPct: shyft.movementPct))
                    .font(.system(size: emphasis == .featured ? 24 : 20, weight: .semibold))
                    .foregroundStyle(tint)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text(shyft.playerName)
                    .font(.system(size: emphasis == .featured ? 28 : 20, weight: .semibold, design: .serif))
                    .foregroundStyle(ShyftyTheme.ink)
                Text(ShyftFormatting.signalSummary(for: shyft))
                    .font(.system(size: emphasis == .featured ? 14 : 13, weight: .medium))
                    .foregroundStyle(ShyftyTheme.ink.opacity(0.95))
                    .lineSpacing(2)
                Text("\(shyft.teamName) • \(ShyftFormatting.metricLabel(for: shyft)) • \(ShyftFormatting.relativeTime(from: shyft.createdAt))")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }
        }
        .padding(emphasis == .featured ? 18 : 16)
        .shyftyPanel(strong: emphasis == .featured)
    }
}

struct ShyftListRowView: View {
    let shyft: Shyft
    var isFollowed: Bool? = nil
    var onFollowToggle: (() -> Void)? = nil

    private var tint: Color { ShyftFormatting.tint(for: shyft.shyftType) }

    private var displayName: String {
        shyft.subjectType == "team" ? shyft.teamName : shyft.playerName
    }

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            RoundedRectangle(cornerRadius: 2, style: .continuous)
                .fill(tint.opacity(0.82))
                .frame(width: 3)

            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .firstTextBaseline) {
                    Text(displayName)
                        .font(.system(size: 20, weight: .semibold, design: .serif))
                        .foregroundStyle(ShyftyTheme.ink)
                    Spacer(minLength: 8)
                    if let isFollowed, let onToggle = onFollowToggle {
                        Button(action: onToggle) {
                            Text(isFollowed ? "✓" : "+")
                                .font(.system(size: 10, weight: .semibold))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .foregroundStyle(isFollowed ? ShyftyTheme.accent : ShyftyTheme.muted)
                                .background(isFollowed ? ShyftyTheme.accentSoft : Color.white.opacity(0.04))
                                .overlay(
                                    Capsule()
                                        .strokeBorder(isFollowed ? ShyftyTheme.accent.opacity(0.3) : ShyftyTheme.border, lineWidth: 1)
                                )
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                    Text(ShyftFormatting.deltaText(current: shyft.currentValue, baseline: shyft.baselineValue, movementPct: shyft.movementPct))
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundStyle(tint)
                }

                Text(ShyftFormatting.signalSummary(for: shyft))
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.ink.opacity(0.96))
                    .lineSpacing(2)

                HStack(spacing: 8) {
                    Text(ShyftFormatting.signalLabel(shyft.shyftType).uppercased())
                        .font(.system(size: 10, weight: .semibold))
                        .kerning(1.4)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 5)
                        .foregroundStyle(tint)
                        .background(tint.opacity(0.12))
                        .clipShape(Capsule())

                    Text("\(shyft.teamName) • \(shyft.leagueName)")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                }

                Text("\(ShyftFormatting.metricLabel(for: shyft)) • \(ShyftFormatting.eventDateText(shyft.eventDate)) • \(ShyftFormatting.relativeTime(from: shyft.createdAt))")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted.opacity(0.9))
            }
        }
        .padding(16)
        .shyftyPanel(strong: true)
    }
}
