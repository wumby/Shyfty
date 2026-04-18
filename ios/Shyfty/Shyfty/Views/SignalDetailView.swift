import SwiftUI

@MainActor
final class SignalDetailViewModel: ObservableObject {
    @Published var trace: SignalTrace?
    @Published var comments: [Comment] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var isFavorited = false
    @Published var draftComment = ""

    let signalId: Int

    init(signalId: Int, prefetchedSignal: Signal? = nil) {
        self.signalId = signalId
        if let s = prefetchedSignal {
            self.isFavorited = s.isFavorited
        }
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            let fetched = try await APIClient.shared.fetchSignalDetail(id: signalId)
            trace = fetched
            comments = fetched.discussionPreview
            isFavorited = fetched.signal.isFavorited
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func toggleFavorite() async {
        let was = isFavorited
        isFavorited = !was
        do {
            if was {
                try await APIClient.shared.removeFavorite(signalId: signalId)
            } else {
                try await APIClient.shared.addFavorite(signalId: signalId)
            }
        } catch {
            isFavorited = was
        }
    }

    func react(type: String) async {
        guard let signal = trace?.signal else { return }
        do {
            if signal.userReaction == type {
                try await APIClient.shared.clearReaction(signalId: signalId)
            } else {
                try await APIClient.shared.setReaction(signalId: signalId, type: type)
            }
            await load()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func postComment() async {
        let body = draftComment.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return }
        do {
            let comment = try await APIClient.shared.postComment(signalId: signalId, body: body)
            comments.append(comment)
            draftComment = ""
        } catch {
            errorMessage = error.localizedDescription
        }
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
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await viewModel.toggleFavorite() }
                } label: {
                    Image(systemName: viewModel.isFavorited ? "star.fill" : "star")
                        .foregroundStyle(viewModel.isFavorited ? ShyftyTheme.warning : ShyftyTheme.muted)
                }
            }
        }
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
                        NavigationLink(value: signal.playerID) {
                            Text("Player context")
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.ink)
                        }
                        Text("•")
                            .foregroundStyle(ShyftyTheme.muted)
                        Text(signal.teamName)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(ShyftyTheme.ink)
                        Text("•")
                            .foregroundStyle(ShyftyTheme.muted)
                        Text(signal.metricLabel.uppercased())
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(ShyftyTheme.muted)
                    }

                    if let freshness = signal.freshness {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(freshness.label)
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundStyle(freshness.state == "stale" ? ShyftyTheme.danger : ShyftyTheme.ink)
                            Text(freshness.coverageSummary)
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                            if let delayed = freshness.delayedDataMessage {
                                Text(delayed)
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.muted)
                            }
                        }
                        .padding(14)
                        .shyftyPanel()
                    }
                }
                .padding(18)
                .shyftyPanel()

                HStack(spacing: 12) {
                    metricCell(label: "This Game", value: "\(signal.currentValue, specifier: "%.1f")", color: tint)
                    metricCell(label: "Baseline", value: "\(signal.baselineValue, specifier: "%.1f")", color: ShyftyTheme.muted)
                    metricCell(label: "Z-Score", value: "\(signal.zScore >= 0 ? "+" : "")\(signal.zScore, specifier: "%.2f")", color: ShyftyTheme.ink)
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
                relatedSection(trace.relatedSignals)
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
        VStack(alignment: .leading, spacing: 12) {
            Text("Reactions")
                .shyftyEyebrow()

            HStack(spacing: 10) {
                reactionPill(label: "Strong", count: signal.reactionSummary.strong, active: signal.userReaction == "strong", color: ShyftyTheme.success) {
                    Task { await viewModel.react(type: "strong") }
                }
                reactionPill(label: "Agree", count: signal.reactionSummary.agree, active: signal.userReaction == "agree", color: ShyftyTheme.accent) {
                    Task { await viewModel.react(type: "agree") }
                }
                reactionPill(label: "Risky", count: signal.reactionSummary.risky, active: signal.userReaction == "risky", color: ShyftyTheme.warning) {
                    Task { await viewModel.react(type: "risky") }
                }
            }
        }
        .padding(18)
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
                .foregroundStyle(ShyftyTheme.ink)
            }
        }
        .padding(18)
        .shyftyPanel()
    }

    @ViewBuilder
    private func relatedSection(_ signals: [Signal]) -> some View {
        if !signals.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                Text("Related Signals")
                    .shyftyEyebrow()
                ForEach(signals) { signal in
                    NavigationLink {
                        SignalDetailView(signalId: signal.id, signal: signal)
                    } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(signal.playerName)
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.ink)
                            Text(signal.explanation)
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(Color.white.opacity(0.03))
                        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(ShyftyTheme.border, lineWidth: 1))
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(18)
            .shyftyPanel()
        }
    }

    private func reactionPill(label: String, count: Int, active: Bool, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Text(label)
                    .font(.system(size: 11, weight: .semibold))
                    .tracking(1.4)
                    .textCase(.uppercase)
                if count > 0 {
                    Text("\(count)")
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 9)
            .foregroundStyle(active ? color : ShyftyTheme.muted)
            .background(active ? color.opacity(0.12) : Color.white.opacity(0.03))
            .overlay(Capsule().strokeBorder(active ? color.opacity(0.3) : ShyftyTheme.border, lineWidth: 1))
            .clipShape(Capsule())
        }
        .buttonStyle(.plain)
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
