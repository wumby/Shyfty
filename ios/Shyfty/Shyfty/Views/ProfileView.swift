import SwiftUI

struct ProfileView: View {
    @EnvironmentObject private var auth: AuthViewModel

    var body: some View {
        ZStack {
            ShyftyBackground()

            ScrollView {
                VStack(spacing: 18) {
                    if let user = auth.currentUser {
                        signedInView(user)
                    } else {
                        signedOutView
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
            }
        }
        .navigationTitle("Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .sheet(isPresented: $auth.showAuthSheet) {
            AuthView()
                .environmentObject(auth)
        }
    }

    private func signedInView(_ user: AuthUser) -> some View {
        VStack(spacing: 18) {
            VStack(spacing: 10) {
                Image(systemName: "person.crop.circle.fill")
                    .font(.system(size: 56))
                    .foregroundStyle(ShyftyTheme.accent)
                Text("Profile")
                    .shyftyHeadline(30)
                Text(user.email)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(ShyftyTheme.ink)
                Text("Member since \(formattedDate(user.createdAt))")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }
            .padding(24)
            .shyftyPanel()

            Button {
                Task {
                    await auth.signOut()
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
    }

    private var signedOutView: some View {
        VStack(spacing: 18) {
            VStack(spacing: 10) {
                Image(systemName: "person.crop.circle.badge.plus")
                    .font(.system(size: 54))
                    .foregroundStyle(ShyftyTheme.accent)
                Text("Sign in for reactions, saved players, and a more personal board.")
                    .shyftyHeadline(28)
                    .multilineTextAlignment(.center)
                Text("Keep profile actions tucked away here instead of competing with the main reading surfaces.")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
                    .multilineTextAlignment(.center)
            }
            .padding(24)
            .shyftyPanel()

            Button {
                auth.isSignUp = false
                auth.showAuthSheet = true
            } label: {
                Text("Sign In")
                    .font(.system(size: 12, weight: .semibold))
                    .tracking(2)
                    .textCase(.uppercase)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(ShyftyTheme.accent)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
            }
        }
    }

    private func formattedDate(_ iso: String) -> String {
        let fmt = ISO8601DateFormatter()
        guard let date = fmt.date(from: iso) else { return iso }
        return date.formatted(.dateTime.month().year())
    }
}
