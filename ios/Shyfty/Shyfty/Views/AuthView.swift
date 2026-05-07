import SwiftUI

struct AuthView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var email = ""
    @State private var password = ""
    @State private var displayName = ""

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                VStack(spacing: 0) {
                    Spacer()

                    VStack(spacing: 28) {
                        VStack(spacing: 10) {
                            HStack(spacing: 8) {
                                ShyftyAccentDot()
                                Text("Access")
                                    .shyftyEyebrow()
                            }
                            Text(auth.isSignUp ? "Create account" : "Welcome back")
                                .shyftyHeadline(32)
                            Text(auth.isSignUp
                                 ? "Track player shyfts and build your personalized feed."
                                 : "Sign in to react, comment, and follow players.")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 8)
                        }

                        VStack(spacing: 12) {
                            if auth.isSignUp {
                                TextField("Display Name (optional)", text: $displayName)
                                    .autocorrectionDisabled()
                                    .textInputAutocapitalization(.words)
                                    .shyftyField()
                            }

                            TextField("Email", text: $email)
                                .keyboardType(.emailAddress)
                                .autocorrectionDisabled()
                                .textInputAutocapitalization(.never)
                                .shyftyField()

                            SecureField("Password", text: $password)
                                .shyftyField()

                            if let error = auth.errorMessage {
                                Text(error)
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.danger)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }

                            Button {
                                Task {
                                    if auth.isSignUp {
                                        await auth.signUp(email: email, password: password, displayName: displayName)
                                    } else {
                                        await auth.signIn(email: email, password: password)
                                    }
                                    if auth.currentUser != nil { dismiss() }
                                }
                            } label: {
                                Group {
                                    if auth.isLoading {
                                        ProgressView()
                                            .tint(.white)
                                    } else {
                                        Text(auth.isSignUp ? "Create Account" : "Sign In")
                                            .font(.system(size: 12, weight: .semibold))
                                            .tracking(2)
                                            .textCase(.uppercase)
                                    }
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(ShyftyTheme.accent)
                                .foregroundStyle(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                            }
                            .disabled(auth.isLoading || email.isEmpty || password.isEmpty)
                        }

                        Button {
                            auth.isSignUp.toggle()
                            auth.errorMessage = nil
                        } label: {
                            HStack(spacing: 4) {
                                Text(auth.isSignUp ? "Already have an account?" : "Don't have an account?")
                                    .foregroundStyle(ShyftyTheme.muted)
                                Text(auth.isSignUp ? "Sign In" : "Create one")
                                    .foregroundStyle(Color(red: 1.0, green: 0.85, blue: 0.74))
                            }
                            .font(.system(size: 12, weight: .medium))
                        }

                        if !auth.isSignUp {
                            if let frontendURL = Bundle.main.object(forInfoDictionaryKey: "ShyftyFrontendURL") as? String,
                               let url = URL(string: "\(frontendURL.trimmingCharacters(in: .init(charactersIn: "/")))/reset-password") {
                                Link("Forgot password?", destination: url)
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(ShyftyTheme.muted)
                            }
                        }
                    }
                    .padding(28)
                    .shyftyPanel()
                    .padding(.horizontal, 18)

                    Spacer()
                }
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Cancel") { dismiss() }
                        .foregroundStyle(ShyftyTheme.muted)
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}
