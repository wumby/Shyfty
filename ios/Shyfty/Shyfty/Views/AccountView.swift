import SwiftUI

struct AccountView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @State private var globalMessage: String?

    var body: some View {
        NavigationStack {
            ZStack {
                ShyftyBackground()

                if let user = auth.currentUser {
                    signedInContent(user: user)
                } else {
                    signedOutContent
                }
            }
            .navigationTitle("Account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
        }
        .preferredColorScheme(.dark)
        .sheet(isPresented: $auth.showAuthSheet) {
            AuthView()
                .environmentObject(auth)
        }
    }

    private func signedInContent(user: AuthUser) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 10) {
                    sectionHeader("Profile")
                    HStack(spacing: 14) {
                        Image(systemName: "person.crop.circle.fill")
                            .font(.system(size: 46))
                            .foregroundStyle(ShyftyTheme.accent)

                        VStack(alignment: .leading, spacing: 4) {
                            Text(resolvedDisplayName(user))
                                .font(.system(size: 18, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.ink)
                            Text(user.email)
                                .font(.system(size: 13, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted)
                                .lineLimit(1)
                            Text("Member since \(formattedDate(user.createdAt))")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(ShyftyTheme.muted.opacity(0.85))
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(16)
                    .shyftyPanel(strong: true)
                }

                VStack(alignment: .leading, spacing: 10) {
                    sectionHeader("Account Actions")
                    VStack(spacing: 0) {
                        NavigationLink {
                            EditProfileView(
                                initialDisplayName: user.displayName ?? "",
                                onSaved: { message in
                                    globalMessage = message
                                }
                            )
                            .environmentObject(auth)
                        } label: {
                            settingsRow("Edit Profile")
                        }
                        Divider()
                            .overlay(ShyftyTheme.border.opacity(0.9))
                            .padding(.leading, 16)
                        NavigationLink {
                            ChangePasswordView(
                                onSuccess: { message in
                                    globalMessage = message
                                }
                            )
                            .environmentObject(auth)
                        } label: {
                            settingsRow("Change Password")
                        }
                    }
                    .shyftyPanel(strong: true)
                }

                VStack(alignment: .leading, spacing: 10) {
                    sectionHeader("Danger Zone")
                    HStack {
                        Spacer()
                        Button {
                            Task { await auth.signOut() }
                        } label: {
                            Text("Sign Out")
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundStyle(ShyftyTheme.danger)
                        }
                        .buttonStyle(.plain)
                        Spacer()
                    }
                    .padding(.vertical, 14)
                    .shyftyPanel(strong: true)
                }

                if let globalMessage {
                    Text(globalMessage)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(ShyftyTheme.muted)
                        .padding(.horizontal, 4)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
        }
    }

    private var signedOutContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                sectionHeader("Profile")
                VStack(spacing: 8) {
                    Text(globalMessage ?? "Sign in to manage your account.")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(globalMessage == nil ? ShyftyTheme.muted : ShyftyTheme.success)
                        .multilineTextAlignment(.center)

                    Button("Sign In") {
                        auth.isSignUp = false
                        auth.showAuthSheet = true
                    }
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(ShyftyTheme.accent)
                    .buttonStyle(.plain)
                }
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(18)
                .shyftyPanel(strong: true)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
        }
    }

    private func resolvedDisplayName(_ user: AuthUser) -> String {
        if let displayName = user.displayName, !displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return displayName
        }
        return user.email.split(separator: "@").first.map(String.init) ?? user.email
    }

    private func formattedDate(_ iso: String) -> String {
        let withFractional = ISO8601DateFormatter()
        withFractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let basic = ISO8601DateFormatter()
        basic.formatOptions = [.withInternetDateTime]

        let fallback = DateFormatter()
        fallback.locale = Locale(identifier: "en_US_POSIX")
        fallback.dateFormat = "yyyy-MM-dd HH:mm:ss"

        guard let date = withFractional.date(from: iso)
            ?? basic.date(from: iso)
            ?? fallback.date(from: iso.replacingOccurrences(of: "T", with: " ").replacingOccurrences(of: "Z", with: ""))
        else { return iso }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    private func settingsRow(_ title: String) -> some View {
        HStack {
            Text(title)
                .font(.system(size: 15, weight: .medium))
                .foregroundStyle(ShyftyTheme.ink)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(ShyftyTheme.muted.opacity(0.7))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 11, weight: .semibold))
            .tracking(1.0)
            .foregroundStyle(ShyftyTheme.muted.opacity(0.85))
            .textCase(.uppercase)
    }
}

private struct EditProfileView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.dismiss) private var dismiss

    let initialDisplayName: String
    let onSaved: (String) -> Void

    @State private var displayName: String = ""
    @State private var isSaving = false
    @State private var errorMessage: String?

    var body: some View {
        Form {
            Section("Profile") {
                TextField("Display Name", text: $displayName)
                    .textInputAutocapitalization(.words)
                    .autocorrectionDisabled()
            }
        }
        .scrollContentBackground(.hidden)
        .background(ShyftyTheme.bgDeep)
        .navigationTitle("Edit Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Save") {
                    Task { await save() }
                }
                .disabled(isSaving)
            }
        }
        .task {
            displayName = initialDisplayName
        }
        .alert("Couldn’t Save", isPresented: Binding(get: { errorMessage != nil }, set: { _ in errorMessage = nil })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    @MainActor
    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            _ = try await APIClient.shared.updateProfile(displayName: displayName)
            await auth.refreshSession()
            onSaved("Profile updated.")
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private struct ChangePasswordView: View {
    @EnvironmentObject private var auth: AuthViewModel
    @Environment(\.dismiss) private var dismiss

    let onSuccess: (String) -> Void

    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var isSubmitting = false
    @State private var message: String?

    var body: some View {
        Form {
            Section("Password") {
                SecureField("Current Password", text: $currentPassword)
                SecureField("New Password", text: $newPassword)
                SecureField("Confirm New Password", text: $confirmPassword)
            }

            if let message {
                Section {
                    Text(message)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(message.contains("success") ? ShyftyTheme.success : ShyftyTheme.danger)
                }
            }

            Section {
                Button {
                    Task { await submit() }
                } label: {
                    HStack {
                        Spacer()
                        Text(isSubmitting ? "Updating..." : "Update Password")
                            .font(.system(size: 15, weight: .semibold))
                        Spacer()
                    }
                }
                .disabled(isSubmitting)
            }
        }
        .scrollContentBackground(.hidden)
        .background(ShyftyTheme.bgDeep)
        .navigationTitle("Change Password")
        .navigationBarTitleDisplayMode(.inline)
    }

    @MainActor
    private func submit() async {
        message = nil
        let current = currentPassword.trimmingCharacters(in: .whitespacesAndNewlines)
        let next = newPassword.trimmingCharacters(in: .whitespacesAndNewlines)
        let confirm = confirmPassword.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !current.isEmpty, !next.isEmpty, !confirm.isEmpty else {
            message = "Please fill out all fields."
            return
        }
        guard next == confirm else {
            message = "New password and confirmation do not match."
            return
        }
        guard next.count >= 8,
              next.rangeOfCharacter(from: .letters) != nil,
              next.rangeOfCharacter(from: .decimalDigits) != nil else {
            message = "Use at least 8 characters with letters and numbers."
            return
        }

        isSubmitting = true
        defer { isSubmitting = false }

        do {
            let responseMessage = try await APIClient.shared.changePassword(
                currentPassword: current,
                newPassword: next,
                confirmNewPassword: confirm
            )
            await auth.signOut()
            onSuccess(responseMessage)
            dismiss()
        } catch let apiError as APIError {
            switch apiError {
            case .httpError(429, _):
                message = "Too many attempts. Try again shortly."
            case .httpError(_, let detail):
                message = detail
            case .decodingError:
                message = "Server response could not be read."
            }
        } catch {
            message = "Network/server error. Please try again."
        }
    }
}
