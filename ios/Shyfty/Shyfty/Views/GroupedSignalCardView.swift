import SwiftUI

struct TeamNavigationTarget: Hashable {
    let teamID: Int
}

struct GroupedSignalCardView: View {
    let signals: [Signal]
    var isFollowed: Bool? = nil
    var onFollowToggle: (() -> Void)? = nil

    @EnvironmentObject private var auth: AuthViewModel
    @State private var selectedCommentSignal: Signal?
    @State private var isMutatingReaction = false

    private var sorted: [Signal] {
        signals.sorted { $0.importance > $1.importance }
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
            .sheet(item: $selectedCommentSignal) { signal in
                SignalCommentsSheetView(signal: signal)
                    .environmentObject(auth)
                    .presentationDetents([.medium, .large])
            }
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
                    NavigationLink(value: TeamNavigationTarget(teamID: signal.teamID)) {
                        Text(name)
                            .font(.system(size: 22, weight: .semibold, design: .serif))
                            .foregroundStyle(ShyftyTheme.ink)
                    }
                    .buttonStyle(.plain)
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

    @ViewBuilder
    private func engagementControls(_ signal: Signal) -> some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 8) {
                reactionButton(signal: signal, type: "strong", label: "Strong", count: signal.reactionSummary.strong, color: ShyftyTheme.success)
                reactionButton(signal: signal, type: "agree", label: "Agree", count: signal.reactionSummary.agree, color: ShyftyTheme.accent)
                reactionButton(signal: signal, type: "risky", label: "Risky", count: signal.reactionSummary.risky, color: ShyftyTheme.warning)

                Spacer(minLength: 8)

                Button {
                    selectedCommentSignal = signal
                } label: {
                    HStack(spacing: 5) {
                        Image(systemName: "bubble.left")
                            .font(.system(size: 11, weight: .semibold))
                        Text(signal.commentCount > 0 ? "\(signal.commentCount)" : "Comment")
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
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
    }

    private func reactionButton(signal: Signal, type: String, label: String, count: Int, color: Color) -> some View {
        let active = signal.userReaction == type
        let disabled = isMutatingReaction || (signal.userReaction != nil && !active)
        return Button {
            Task { await react(signal: signal, type: type) }
        } label: {
            HStack(spacing: 5) {
                Text(label)
                    .font(.system(size: 10, weight: .semibold))
                    .tracking(0.7)
                    .textCase(.uppercase)
                if count > 0 {
                    Text("\(count)")
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .foregroundStyle(active ? color : ShyftyTheme.muted)
            .background(active ? color.opacity(0.13) : Color.white.opacity(0.03))
            .overlay(Capsule().strokeBorder(active ? color.opacity(0.35) : ShyftyTheme.border, lineWidth: 1))
            .clipShape(Capsule())
            .opacity(disabled ? 0.42 : 1)
        }
        .disabled(disabled)
        .buttonStyle(.plain)
    }

    @MainActor
    private func react(signal: Signal, type: String) async {
        guard auth.currentUser != nil else {
            auth.showAuthSheet = true
            return
        }
        guard !isMutatingReaction else { return }

        let nextUserReaction = signal.userReaction == type ? nil : type
        let nextSignal = signal.withReaction(
            reactionSummary: updatedReactionSummary(from: signal, nextUserReaction: nextUserReaction),
            userReaction: nextUserReaction
        )

        isMutatingReaction = true
        postEngagementChange(nextSignal)
        do {
            if signal.userReaction == type {
                try await APIClient.shared.clearReaction(signalId: signal.id)
            } else {
                try await APIClient.shared.setReaction(signalId: signal.id, type: type)
            }
        } catch {
            postEngagementChange(signal)
        }
        isMutatingReaction = false
    }

    private func updatedReactionSummary(from signal: Signal, nextUserReaction: String?) -> ReactionSummary {
        let current = signal.reactionSummary
        func adjusted(_ label: String, _ value: Int) -> Int {
            var next = value
            if signal.userReaction == label { next -= 1 }
            if nextUserReaction == label { next += 1 }
            return max(0, next)
        }
        return ReactionSummary(
            strong: adjusted("strong", current.strong),
            agree: adjusted("agree", current.agree),
            risky: adjusted("risky", current.risky)
        )
    }

    private func postEngagementChange(_ signal: Signal) {
        NotificationCenter.default.post(
            name: .signalEngagementDidChange,
            object: nil,
            userInfo: [
                "signalId": signal.id,
                "reactionSummary": signal.reactionSummary,
                "userReaction": signal.userReaction ?? NSNull(),
                "commentCount": signal.commentCount,
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
