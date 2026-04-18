import SwiftUI

struct AccountView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                VStack(spacing: 24) {
                    Spacer()

                    VStack(spacing: 20) {
                        VStack(spacing: 10) {
                            Image(systemName: "person.crop.circle.fill")
                                .font(.system(size: 56))
                                .foregroundStyle(ShyftyTheme.accent)
                            Text("Account")
                                .shyftyHeadline(30)
                            if let user = auth.currentUser {
                                Text(user.email)
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.ink)
                                Text("Member since \(formattedDate(user.createdAt))")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.muted)
                            }
                        }

                        Button {
                            Task {
                                await auth.signOut()
                                dismiss()
                            }
                        } label: {
                            Text("Sign Out")
                                .font(.system(size: 12, weight: .semibold))
                                .tracking(2)
                                .textCase(.uppercase)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(ShyftyTheme.accentSoft)
                                .foregroundStyle(Color(red: 1.0, green: 0.85, blue: 0.74))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                                        .strokeBorder(ShyftyTheme.accent.opacity(0.34), lineWidth: 1)
                                )
                                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                        }
                    }
                    .padding(28)
                    .shyftyPanel()
                    .padding(.horizontal, 18)

                    Spacer()
                }
            }
            .navigationTitle("Account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundStyle(ShyftyTheme.muted)
                }
            }
        }
        .preferredColorScheme(.dark)
    }

    private func formattedDate(_ iso: String) -> String {
        let fmt = ISO8601DateFormatter()
        guard let date = fmt.date(from: iso) else { return iso }
        return date.formatted(.dateTime.month().year())
    }
}
