import SwiftUI

struct AuthView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var email = ""
    @State private var password = ""

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                VStack(spacing: 0) {
                    Spacer()

                    VStack(spacing: 28) {
                        // Header
                        VStack(spacing: 8) {
                            Text("SHYFTY")
                                .font(.caption.weight(.semibold))
                                .kerning(3)
                                .foregroundStyle(.cyan)
                            Text(auth.isSignUp ? "Create account" : "Welcome back")
                                .font(.title.bold())
                            Text(auth.isSignUp
                                 ? "Track player signals and build your personalized feed."
                                 : "Sign in to react, comment, and follow players.")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 8)
                        }

                        // Form
                        VStack(spacing: 12) {
                            TextField("Email", text: $email)
                                .keyboardType(.emailAddress)
                                .autocorrectionDisabled()
                                .textInputAutocapitalization(.never)
                                .padding()
                                .background(Color.white.opacity(0.07))
                                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                            SecureField("Password", text: $password)
                                .padding()
                                .background(Color.white.opacity(0.07))
                                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                            if let error = auth.errorMessage {
                                Text(error)
                                    .font(.footnote)
                                    .foregroundStyle(.red)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }

                            Button {
                                Task {
                                    if auth.isSignUp {
                                        await auth.signUp(email: email, password: password)
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
                                            .font(.body.weight(.semibold))
                                    }
                                }
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color.blue)
                                .foregroundStyle(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                            }
                            .disabled(auth.isLoading || email.isEmpty || password.isEmpty)
                        }

                        // Toggle sign in / sign up
                        Button {
                            auth.isSignUp.toggle()
                            auth.errorMessage = nil
                        } label: {
                            HStack(spacing: 4) {
                                Text(auth.isSignUp ? "Already have an account?" : "Don't have an account?")
                                    .foregroundStyle(.secondary)
                                Text(auth.isSignUp ? "Sign In" : "Create one")
                                    .foregroundStyle(.blue)
                            }
                            .font(.footnote)
                        }
                    }
                    .padding(28)

                    Spacer()
                }
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Cancel") { dismiss() }
                        .foregroundStyle(.secondary)
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}
