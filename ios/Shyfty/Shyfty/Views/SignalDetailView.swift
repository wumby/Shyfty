import SwiftUI

@MainActor
final class SignalDetailViewModel: ObservableObject {
    @Published var trace: SignalTrace?
    @Published var comments: [Comment] = []
    @Published var isLoading = false
    @Published var isMutatingReaction = false
    @Published var isPostingComment = false
    @Published var errorMessage: String?
    @Published var draftComment = ""

    let signalId: Int

    init(signalId: Int, prefetchedSignal: Signal? = nil) {
        self.signalId = signalId
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            let fetched = try await APIClient.shared.fetchSignalDetail(id: signalId)
            trace = fetched
            comments = fetched.discussionPreview
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func react(type: ShyftReaction) async {
        guard let signal = trace?.signal else { return }
        let previousTrace = trace
        let isTogglingOff = signal.userReaction == type
        let nextUserReaction: ShyftReaction? = isTogglingOff ? nil : type
        let nextSummary = updatedReactionSummary(from: signal, nextUserReaction: nextUserReaction)
        patchSignal(signal.withReaction(reactionSummary: nextSummary, userReaction: nextUserReaction))
        isMutatingReaction = true
        errorMessage = nil
        do {
            if isTogglingOff {
                try await APIClient.shared.clearReaction(signalId: signalId)
            } else {
                try await APIClient.shared.setReaction(signalId: signalId, type: type)
            }
        } catch {
            trace = previousTrace
            errorMessage = error.localizedDescription
        }
        isMutatingReaction = false
    }

    func postComment() async {
        let body = draftComment.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return }
        isPostingComment = true
        errorMessage = nil
        do {
            let comment = try await APIClient.shared.postComment(signalId: signalId, body: body)
            comments.append(comment)
            draftComment = ""
            if let signal = trace?.signal {
                patchSignal(signal.withCommentCount(signal.commentCount + 1))
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isPostingComment = false
    }

    private func updatedReactionSummary(from signal: Signal, nextUserReaction: ShyftReaction?) -> ReactionSummary {
        let current = signal.reactionSummary
        func adjusted(_ reaction: ShyftReaction, _ value: Int) -> Int {
            var next = value
            if signal.userReaction == reaction { next -= 1 }
            if nextUserReaction == reaction { next += 1 }
            return max(0, next)
        }
        return ReactionSummary(
            shyftUp: adjusted(.shyftUp, current.shyftUp),
            shyftDown: adjusted(.shyftDown, current.shyftDown),
            shyftEye: adjusted(.shyftEye, current.shyftEye)
        )
    }

    private func patchSignal(_ signal: Signal) {
        guard let trace else { return }
        self.trace = SignalTrace(
            signal: signal,
            rollingMetric: trace.rollingMetric,
            sourceStat: trace.sourceStat,
            baselineSamples: trace.baselineSamples,
            discussionPreview: trace.discussionPreview,
            feedContext: trace.feedContext
        )
        NotificationCenter.default.post(
            name: .signalEngagementDidChange,
            object: nil,
            userInfo: [
                "signalId": signal.id,
                "reactionSummary": signal.reactionSummary,
                "userReaction": signal.userReaction?.rawValue ?? NSNull(),
                "commentCount": signal.commentCount,
            ]
        )
    }
}

struct SignalDetailView: View {
    let signalId: Int
    let prefetchedSignal: Signal?

    @StateObject private var viewModel: SignalDetailViewModel
    @State private var provenanceExpanded = false

    init(signalId: Int, signal: Signal? = nil) {
        self.signalId = signalId
        self.prefetchedSignal = signal
        _viewModel = StateObject(wrappedValue: SignalDetailViewModel(signalId: signalId, prefetchedSignal: signal))
    }

    var body: some View {
        ZStack {
            ShyftyBackground()
            content
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task { await viewModel.load() }
        .preferredColorScheme(.dark)
    }

    @ViewBuilder
    private var content: some View {
        if viewModel.isLoading && viewModel.trace == nil {
            ProgressView().tint(ShyftyTheme.accent)
        } else if let error = viewModel.errorMessage {
            Text(error).foregroundStyle(ShyftyTheme.danger)
        } else if let trace = viewModel.trace {
            detailScroll(trace: trace)
        } else if let signal = prefetchedSignal {
            ScrollView {
                SignalCardView(signal: signal)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
            }
        }
    }

    private func detailScroll(trace: SignalTrace) -> some View {
        let signal = trace.signal
        let tint = SignalFormatting.tint(for: signal.signalType)

        return ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 8) {
                        Text(SignalFormatting.signalLabel(signal.signalType).uppercased())
                            .font(.system(size: 10, weight: .semibold))
                            .kerning(1.6)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .foregroundStyle(tint)
                            .background(tint.opacity(0.12))
                            .overlay(Capsule().strokeBorder(tint.opacity(0.22), lineWidth: 1))
                            .clipShape(Capsule())
                        Spacer()
                    }

                    Text(signal.playerName)
                        .shyftyHeadline(32)

                    HStack(spacing: 8) {
                        if let playerID = signal.playerID {
                            NavigationLink(value: playerID) {
                                Text("Player context")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundStyle(ShyftyTheme.ink)
                            }
                            Text("•")
                                .foregroundStyle(ShyftyTheme.muted)
                        }
                        Text(signal.teamName)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(ShyftyTheme.ink)
                        Text("•")
                            .foregroundStyle(ShyftyTheme.muted)
                        Text(signal.metricLabel.uppercased())
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(ShyftyTheme.muted)
                    }

                }
                .padding(18)
                .shyftyPanel()

                HStack(spacing: 12) {
                    metricCell(label: "This Game", value: String(format: "%.1f", signal.currentValue), color: tint)
                    metricCell(label: "Baseline", value: String(format: "%.1f", signal.baselineValue), color: ShyftyTheme.muted)
                    metricCell(label: "Z-Score", value: "\(signal.zScore >= 0 ? "+" : "")\(String(format: "%.2f", signal.zScore))", color: ShyftyTheme.ink)
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("What This Means")
                        .shyftyEyebrow()
                    Text(signal.explanation)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(Color(red: 0.85, green: 0.89, blue: 0.95))
                        .lineSpacing(3)
                }
                .padding(18)
                .shyftyPanel()

                provenanceSection(trace: trace)
                reactionSection(signal: signal)
                discussionSection
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
        }
    }

    @ViewBuilder
    private func provenanceSection(trace: SignalTrace) -> some View {
        let signal = trace.signal
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    provenanceExpanded.toggle()
                }
            } label: {
                HStack {
                    Text("Why It Triggered")
                        .shyftyEyebrow()
                    Spacer()
                    Image(systemName: provenanceExpanded ? "chevron.up" : "chevron.down")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(ShyftyTheme.muted)
                }
                .padding(18)
            }

            if provenanceExpanded {
                VStack(alignment: .leading, spacing: 14) {
                    if let reason = signal.classificationReason {
                        Text(reason)
                            .font(.system(size: 11, weight: .semibold))
                            .tracking(1.4)
                            .textCase(.uppercase)
                            .foregroundStyle(ShyftyTheme.muted)
                    }

                    if !trace.baselineSamples.isEmpty {
                        ForEach(trace.baselineSamples.prefix(4)) { sample in
                            HStack {
                                Text(sample.gameDate)
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.muted)
                                Spacer()
                                Text("\(sample.value, specifier: "%.1f")")
                                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                    .foregroundStyle(ShyftyTheme.ink)
                            }
                        }
                    }

                    Text(signal.baselineWindow)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted.opacity(0.75))
                }
                .padding(.horizontal, 18)
                .padding(.bottom, 18)
            }
        }
        .shyftyPanel()
    }

    @ViewBuilder
    private func reactionSection(signal: Signal) -> some View {
        HStack(spacing: 20) {
            ForEach(ShyftReaction.allCases, id: \.self) { reaction in
                let count = signal.reactionSummary.count(for: reaction)
                let isActive = signal.userReaction == reaction
                Button {
                    Task { await viewModel.react(type: reaction) }
                } label: {
                    HStack(spacing: 5) {
                        ShyftReactionIcon(reaction: reaction, size: 16)
                        if count > 0 {
                            Text("\(count)")
                                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        }
                    }
                    .foregroundStyle(isActive ? Color(red: 1, green: 0.847, blue: 0.741) : ShyftyTheme.muted.opacity(0.4))
                    .scaleEffect(isActive ? 1.1 : 1.0)
                    .shadow(color: isActive ? Color(red: 1, green: 0.847, blue: 0.741).opacity(0.5) : .clear, radius: 4)
                    .animation(.spring(response: 0.25, dampingFraction: 0.7), value: isActive)
                }
                .disabled(viewModel.isMutatingReaction)
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .shyftyPanel()
    }

    private var discussionSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Discussion")
                .shyftyEyebrow()

            if viewModel.comments.isEmpty {
                Text("No recent comments yet.")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            } else {
                ForEach(viewModel.comments) { comment in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(comment.userEmail.split(separator: "@").first.map(String.init) ?? comment.userEmail)
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.ink)
                            if comment.isEdited {
                                Text("edited")
                                    .font(.system(size: 10, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.muted)
                            }
                        }
                        Text(comment.body)
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(ShyftyTheme.muted)
                    }
                    .padding(12)
                    .background(Color.white.opacity(0.03))
                    .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(ShyftyTheme.border, lineWidth: 1))
                    .clipShape(RoundedRectangle(cornerRadius: 14))
                }
            }

            HStack {
                TextField("Add a comment", text: $viewModel.draftComment, axis: .vertical)
                    .textFieldStyle(.plain)
                    .padding(12)
                    .background(Color.white.opacity(0.03))
                    .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(ShyftyTheme.border, lineWidth: 1))
                    .clipShape(RoundedRectangle(cornerRadius: 14))
                Button("Post") {
                    Task { await viewModel.postComment() }
                }
                .disabled(viewModel.isPostingComment || viewModel.draftComment.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .foregroundStyle(ShyftyTheme.ink)
            }
        }
        .padding(18)
        .shyftyPanel()
    }

    private func metricCell(label: String, value: String, color: Color) -> some View {
        VStack(spacing: 6) {
            Text(label.uppercased())
                .font(.system(size: 10, weight: .semibold))
                .kerning(1.2)
                .foregroundStyle(ShyftyTheme.muted)
            Text(value)
                .font(.system(size: 26, weight: .bold, design: .monospaced))
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 16)
        .shyftyPanel()
    }
}
