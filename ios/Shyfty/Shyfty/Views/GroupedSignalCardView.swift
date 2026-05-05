import SwiftUI

struct TeamNavigationTarget: Hashable {
    let teamID: Int
}

struct GroupedShyftCardView: View {
    let shyfts: [Shyft]
    var isFollowed: Bool? = nil
    var onFollowToggle: (() -> Void)? = nil

    @EnvironmentObject private var auth: AuthViewModel
    @State private var selectedCommentSignal: Shyft?
    @State private var isMutatingReaction = false

    private var sorted: [Shyft] {
        shyfts.sorted { $0.importance > $1.importance }
    }

    var body: some View {
        if let primary = sorted.first {
            VStack(alignment: .leading, spacing: 0) {
                headerRow(primary)
                Color.white.opacity(0.06).frame(height: 1)
                signalRows
                Color.white.opacity(0.06).frame(height: 1)
                engagementControls(primary)
            }
            .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
            .shyftyPanel(strong: true)
            .sheet(item: $selectedCommentSignal) { shyft in
                ShyftCommentsSheetView(shyft: shyft)
                    .environmentObject(auth)
                    .presentationDetents([.medium, .large])
            }
        }
    }

    private func shortName(_ name: String) -> String {
        name.split(separator: " ").last.map(String.init) ?? name
    }

    private func matchupText(_ shyft: Shyft) -> Text {
        let muted = ShyftyTheme.muted
        let dot = Text(" · ").foregroundStyle(muted)

        // Team vs Opponent
        var base: Text
        if let opponent = shyft.opponent, !opponent.isEmpty {
            let side = (shyft.homeAway == "Away" || shyft.homeAway == "@") ? "@" : "vs"
            base = Text("\(shortName(shyft.teamName)) \(side) \(shortName(opponent))").foregroundStyle(muted)
        } else {
            base = Text(shortName(shyft.teamName)).foregroundStyle(muted)
        }

        // W / L + score
        if let result = shyft.gameResult, !result.isEmpty {
            let resultColor: Color = result == "W" ? ShyftyTheme.success : result == "L" ? ShyftyTheme.danger : muted
            base = base + dot + Text(result).foregroundStyle(resultColor)
            if let score = shyft.finalScore, !score.isEmpty {
                let clean = score
                    .replacingOccurrences(of: " - ", with: "–")
                    .replacingOccurrences(of: "-", with: "–")
                base = base + Text(" \(clean)").foregroundStyle(muted)
            }
        }

        // Date — no year
        base = base + dot + Text(ShyftFormatting.eventDateShort(shyft.eventDate)).foregroundStyle(muted)
        return base
    }

    private func headerRow(_ shyft: Shyft) -> some View {
        let name = shyft.subjectType == "team" ? shyft.teamName : shyft.playerName
        return HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                if let playerID = shyft.playerID {
                    NavigationLink(value: playerID) {
                        Text(name)
                            .font(.system(size: 22, weight: .semibold, design: .serif))
                            .foregroundStyle(ShyftyTheme.ink)
                    }
                    .buttonStyle(.plain)
                } else {
                    NavigationLink(value: TeamNavigationTarget(teamID: shyft.teamID)) {
                        Text(name)
                            .font(.system(size: 22, weight: .semibold, design: .serif))
                            .foregroundStyle(ShyftyTheme.ink)
                    }
                    .buttonStyle(.plain)
                }
                matchupText(shyft)
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
        ForEach(Array(sorted.enumerated()), id: \.element.id) { index, shyft in
            NavigationLink(value: shyft) {
                signalRow(shyft)
            }
            .buttonStyle(.plain)
            if index < sorted.count - 1 {
                Color.white.opacity(0.06).frame(height: 1)
            }
        }
    }

    private func signalRow(_ shyft: Shyft) -> some View {
        let tint = ShyftFormatting.tint(for: shyft.shyftType)
        let delta = ShyftFormatting.deltaText(current: shyft.currentValue, baseline: shyft.baselineValue, movementPct: shyft.movementPct)
        let isUp = shyft.trendDirection == "up"
        let isDown = shyft.trendDirection == "down"
        let deltaTone: Color = isUp ? ShyftyTheme.success : isDown ? ShyftyTheme.danger : ShyftyTheme.muted
        let arrow = isUp ? "↑" : isDown ? "↓" : ""

        return HStack(alignment: .top, spacing: 14) {
            RoundedRectangle(cornerRadius: 2, style: .continuous)
                .fill(tint.opacity(0.82))
                .frame(width: 3)

            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    Text(ShyftFormatting.metricLabel(for: shyft))
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.ink)
                        .lineLimit(1)
                    Text(shyft.shyftType)
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
                    Text(formatStat(shyft.currentValue, metricName: shyft.metricName))
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(ShyftyTheme.ink)
                    Text("/")
                        .font(.system(size: 16))
                        .foregroundStyle(ShyftyTheme.muted.opacity(0.5))
                    Text(formatStat(shyft.baselineValue, metricName: shyft.metricName))
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

    @ViewBuilder
    private func engagementControls(_ shyft: Shyft) -> some View {
        HStack(spacing: 0) {
            HStack(spacing: 16) {
                ForEach(ShyftReaction.allCases, id: \.self) { reaction in
                    let count = shyft.reactionSummary.count(for: reaction)
                    let isActive = shyft.userReaction == reaction
                    Button {
                        Task { await react(shyft: shyft, type: reaction) }
                    } label: {
                        HStack(spacing: 4) {
                            ShyftReactionIcon(reaction: reaction, size: 14)
                            if count > 0 {
                                Text("\(count)")
                                    .font(.system(size: 10, weight: .semibold, design: .monospaced))
                            }
                        }
                        .foregroundStyle(isActive ? Color(red: 1, green: 0.847, blue: 0.741) : ShyftyTheme.muted.opacity(0.35))
                        .scaleEffect(isActive ? 1.1 : 1.0)
                        .shadow(color: isActive ? Color(red: 1, green: 0.847, blue: 0.741).opacity(0.45) : .clear, radius: 4)
                        .animation(.spring(response: 0.25, dampingFraction: 0.7), value: isActive)
                    }
                    .disabled(isMutatingReaction)
                    .buttonStyle(.plain)
                }
            }

            Spacer(minLength: 8)

            Button {
                selectedCommentSignal = shyft
            } label: {
                HStack(spacing: 5) {
                    Image(systemName: "bubble.left")
                        .font(.system(size: 11, weight: .semibold))
                    Text(shyft.commentCount > 0 ? "\(shyft.commentCount)" : "Comment")
                        .font(.system(size: 11, weight: .semibold))
                        .lineLimit(1)
                }
                .padding(.horizontal, 11)
                .padding(.vertical, 7)
                .foregroundStyle(ShyftyTheme.muted)
                .background(Color.white.opacity(0.03))
                .overlay(Capsule().strokeBorder(ShyftyTheme.border, lineWidth: 1))
                .clipShape(Capsule())
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
    }

    @MainActor
    private func react(shyft: Shyft, type: ShyftReaction) async {
        guard auth.currentUser != nil else {
            auth.showAuthSheet = true
            return
        }
        guard !isMutatingReaction else { return }

        let isTogglingOff = shyft.userReaction == type
        let nextUserReaction: ShyftReaction? = isTogglingOff ? nil : type
        let nextSignal = shyft.withReaction(
            reactionSummary: updatedReactionSummary(from: shyft, nextUserReaction: nextUserReaction),
            userReaction: nextUserReaction
        )

        isMutatingReaction = true
        postEngagementChange(nextSignal)
        do {
            if isTogglingOff {
                try await APIClient.shared.clearReaction(shyftId: shyft.id)
            } else {
                try await APIClient.shared.setReaction(shyftId: shyft.id, type: type)
            }
        } catch {
            postEngagementChange(shyft)
        }
        isMutatingReaction = false
    }

    private func updatedReactionSummary(from shyft: Shyft, nextUserReaction: ShyftReaction?) -> ReactionSummary {
        let current = shyft.reactionSummary
        func adjusted(_ reaction: ShyftReaction, _ value: Int) -> Int {
            var next = value
            if shyft.userReaction == reaction { next -= 1 }
            if nextUserReaction == reaction { next += 1 }
            return max(0, next)
        }
        return ReactionSummary(
            shyftUp: adjusted(.shyftUp, current.shyftUp),
            shyftDown: adjusted(.shyftDown, current.shyftDown),
            shyftEye: adjusted(.shyftEye, current.shyftEye)
        )
    }

    private func postEngagementChange(_ shyft: Shyft) {
        NotificationCenter.default.post(
            name: .shyftEngagementDidChange,
            object: nil,
            userInfo: [
                "shyftId": shyft.id,
                "reactionSummary": shyft.reactionSummary,
                "userReaction": shyft.userReaction?.rawValue ?? NSNull(),
                "commentCount": shyft.commentCount,
            ]
        )
    }

    private func formatStat(_ value: Double, metricName: String) -> String {
        if metricName == "usage_rate" {
            let normalized = abs(value) <= 1 ? value * 100 : value
            return String(format: "%.1f%%", normalized)
        }
        return value.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(value)) : String(format: "%.1f", value)
    }
}
