import SwiftUI

@MainActor
final class SignalDetailViewModel: ObservableObject {
    @Published var trace: ShyftTrace?
    @Published var comments: [Comment] = []
    @Published var isLoading = false
    @Published var isMutatingReaction = false
    @Published var isPostingComment = false
    @Published var errorMessage: String?
    @Published var draftComment = ""

    let shyftId: Int

    init(shyftId: Int, prefetchedSignal: Shyft? = nil) {
        self.shyftId = shyftId
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            let fetched = try await APIClient.shared.fetchShyftDetail(id: shyftId)
            trace = fetched
            comments = fetched.discussionPreview
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func react(type: ShyftReaction) async {
        guard let shyft = trace?.shyft else { return }
        let previousTrace = trace
        let isTogglingOff = shyft.userReaction == type
        let nextUserReaction: ShyftReaction? = isTogglingOff ? nil : type
        let nextSummary = updatedReactionSummary(from: shyft, nextUserReaction: nextUserReaction)
        patchShyft(shyft.withReaction(reactionSummary: nextSummary, userReaction: nextUserReaction))
        isMutatingReaction = true
        errorMessage = nil
        do {
            if isTogglingOff {
                try await APIClient.shared.clearReaction(shyftId: shyftId)
            } else {
                try await APIClient.shared.setReaction(shyftId: shyftId, type: type)
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
            let comment = try await APIClient.shared.postComment(shyftId: shyftId, body: body)
            comments.append(comment)
            draftComment = ""
            if let shyft = trace?.shyft {
                patchShyft(shyft.withCommentCount(shyft.commentCount + 1))
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isPostingComment = false
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

    private func patchShyft(_ shyft: Shyft) {
        guard let trace else { return }
        self.trace = ShyftTrace(
            shyft: shyft,
            rollingMetric: trace.rollingMetric,
            sourceStat: trace.sourceStat,
            baselineSamples: trace.baselineSamples,
            discussionPreview: trace.discussionPreview,
            feedContext: trace.feedContext
        )
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
}

struct ShyftDetailView: View {
    let shyftId: Int
    let prefetchedSignal: Shyft?

    @StateObject private var viewModel: SignalDetailViewModel
    @State private var provenanceExpanded = false

    init(shyftId: Int, shyft: Shyft? = nil) {
        self.shyftId = shyftId
        self.prefetchedSignal = shyft
        _viewModel = StateObject(wrappedValue: SignalDetailViewModel(shyftId: shyftId, prefetchedSignal: shyft))
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
        } else if let shyft = prefetchedSignal {
            ScrollView {
                ShyftCardView(shyft: shyft)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
            }
        }
    }

    private func detailScroll(trace: ShyftTrace) -> some View {
        let shyft = trace.shyft
        let tint = ShyftFormatting.tint(for: shyft.shyftType)

        return ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 8) {
                        Text(ShyftFormatting.signalLabel(shyft.shyftType).uppercased())
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

                    Text(shyft.playerName)
                        .shyftyHeadline(32)

                    HStack(spacing: 8) {
                        if let playerID = shyft.playerID {
                            NavigationLink(value: playerID) {
                                Text("Player context")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundStyle(ShyftyTheme.ink)
                            }
                            Text("•")
                                .foregroundStyle(ShyftyTheme.muted)
                        }
                        Text(shyft.teamName)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(ShyftyTheme.ink)
                        Text("•")
                            .foregroundStyle(ShyftyTheme.muted)
                        Text(shyft.metricLabel.uppercased())
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(ShyftyTheme.muted)
                    }

                }
                .padding(18)
                .shyftyPanel()

                HStack(spacing: 12) {
                    metricCell(label: "This Game", value: String(format: "%.1f", shyft.currentValue), color: tint)
                    metricCell(label: "Expected", value: String(format: "%.1f", shyft.baselineValue), color: ShyftyTheme.muted)
                    if let movPct = shyft.movementPct {
                        metricCell(
                            label: "Change",
                            value: "\(movPct >= 0 ? "+" : "")\(Int(movPct.rounded()))%",
                            color: ShyftyTheme.ink
                        )
                    } else {
                        metricCell(
                            label: "Deviation",
                            value: "\(shyft.zScore >= 0 ? "+" : "")\(String(format: "%.1f", shyft.zScore))σ",
                            color: ShyftyTheme.ink
                        )
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("What This Means")
                        .shyftyEyebrow()
                    Text(shyft.explanation)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(Color(red: 0.85, green: 0.89, blue: 0.95))
                        .lineSpacing(3)
                }
                .padding(18)
                .shyftyPanel()

                provenanceSection(trace: trace)
                reactionSection(shyft: shyft)
                discussionSection
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
        }
    }

    @ViewBuilder
    private func provenanceSection(trace: ShyftTrace) -> some View {
        let shyft = trace.shyft
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    provenanceExpanded.toggle()
                }
            } label: {
                HStack {
                    Text("Recent History")
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
                    if !trace.baselineSamples.isEmpty {
                        ForEach(trace.baselineSamples.prefix(4)) { sample in
                            HStack {
                                Text(ShyftFormatting.eventDateShort(sample.gameDate))
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.muted)
                                Spacer()
                                Text("\(sample.value, specifier: "%.1f")")
                                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                    .foregroundStyle(ShyftyTheme.ink)
                            }
                        }
                    }

                    Text(shyft.baselineWindow)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted.opacity(0.6))
                }
                .padding(.horizontal, 18)
                .padding(.bottom, 18)
            }
        }
        .shyftyPanel()
    }

    @ViewBuilder
    private func reactionSection(shyft: Shyft) -> some View {
        HStack(spacing: 20) {
            ForEach(ShyftReaction.allCases, id: \.self) { reaction in
                let count = shyft.reactionSummary.count(for: reaction)
                let isActive = shyft.userReaction == reaction
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
