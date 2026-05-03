import SwiftUI

struct SignalCommentsSheetView: View {
    let signal: Signal

    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var comments: [Comment] = []
    @State private var draft = ""
    @State private var isLoading = false
    @State private var isPosting = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()
                VStack(alignment: .leading, spacing: 14) {
                    header
                    commentsList
                    composer
                }
                .padding(16)
            }
            .navigationTitle("Comments")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                        .foregroundStyle(ShyftyTheme.muted)
                }
            }
            .task { await loadComments() }
        }
        .preferredColorScheme(.dark)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(signal.subjectType == "team" ? signal.teamName : signal.playerName)
                .font(.system(size: 22, weight: .semibold, design: .serif))
                .foregroundStyle(ShyftyTheme.ink)
            Text("\(signal.teamName) · \(SignalFormatting.eventDateShort(signal.eventDate))")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
        }
    }

    private var commentsList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 10) {
                if isLoading {
                    ProgressView()
                        .tint(ShyftyTheme.accent)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 32)
                } else if comments.isEmpty {
                    Text("No comments yet.")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(16)
                        .shyftyPanel(strong: true)
                } else {
                    ForEach(comments) { comment in
                        commentRow(comment)
                    }
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(ShyftyTheme.danger)
                        .padding(.top, 4)
                }
            }
        }
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 10) {
            TextField("Add a comment", text: $draft, axis: .vertical)
                .textFieldStyle(.plain)
                .lineLimit(1...4)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.white.opacity(0.04))
                .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(ShyftyTheme.border, lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))

            Button {
                Task { await postComment() }
            } label: {
                Text("Post")
                    .font(.system(size: 12, weight: .semibold))
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .foregroundStyle(ShyftyTheme.ink)
                    .background(ShyftyTheme.accentSoft)
                    .overlay(Capsule().strokeBorder(ShyftyTheme.accent.opacity(0.3), lineWidth: 1))
                    .clipShape(Capsule())
            }
            .disabled(isPosting || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .opacity(isPosting || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.45 : 1)
        }
    }

    private func commentRow(_ comment: Comment) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(spacing: 8) {
                Text(comment.userEmail.split(separator: "@").first.map(String.init) ?? comment.userEmail)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.ink)
                Text(relativeTime(comment.createdAt))
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted.opacity(0.75))
                if comment.isEdited {
                    Text("edited")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted.opacity(0.75))
                }
                Spacer()
                if comment.canDelete {
                    Button("Delete") {
                        Task { await deleteComment(comment) }
                    }
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.danger.opacity(0.85))
                    .buttonStyle(.plain)
                }
            }

            Text(comment.body)
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(ShyftyTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(13)
        .background(Color.white.opacity(0.035))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(ShyftyTheme.border, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    @MainActor
    private func loadComments() async {
        isLoading = true
        errorMessage = nil
        do {
            comments = try await APIClient.shared.fetchComments(signalId: signal.id)
            postCommentCount(comments.count)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    @MainActor
    private func postComment() async {
        guard auth.currentUser != nil else {
            auth.showAuthSheet = true
            return
        }
        let body = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return }
        isPosting = true
        errorMessage = nil
        do {
            let comment = try await APIClient.shared.postComment(signalId: signal.id, body: body)
            comments.append(comment)
            draft = ""
            postCommentCount(comments.count)
        } catch {
            errorMessage = error.localizedDescription
        }
        isPosting = false
    }

    @MainActor
    private func deleteComment(_ comment: Comment) async {
        let previous = comments
        comments.removeAll { $0.id == comment.id }
        postCommentCount(comments.count)
        do {
            try await APIClient.shared.deleteComment(commentId: comment.id)
        } catch {
            comments = previous
            postCommentCount(previous.count)
            errorMessage = error.localizedDescription
        }
    }

    private func postCommentCount(_ count: Int) {
        let patched = signal.withCommentCount(count)
        NotificationCenter.default.post(
            name: .signalEngagementDidChange,
            object: nil,
            userInfo: [
                "signalId": patched.id,
                "reactionSummary": patched.reactionSummary,
                "userReaction": patched.userReaction?.rawValue ?? NSNull(),
                "commentCount": patched.commentCount,
            ]
        )
    }

    private func relativeTime(_ iso: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: iso) else { return "" }
        let seconds = Int(Date().timeIntervalSince(date))
        if seconds < 60 { return "now" }
        if seconds < 3600 { return "\(seconds / 60)m" }
        if seconds < 86_400 { return "\(seconds / 3600)h" }
        return "\(seconds / 86_400)d"
    }
}
