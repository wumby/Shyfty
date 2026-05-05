import Foundation
import SwiftUI

@MainActor
final class AuthViewModel: ObservableObject {
    @Published var currentUser: AuthUser?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var showAuthSheet = false
    @Published var isSignUp = false

    func refreshSession() async {
        do {
            let session = try await APIClient.shared.fetchSession()
            currentUser = session.user
        } catch {
            currentUser = nil
        }
    }

    func signIn(email: String, password: String) async {
        isLoading = true
        errorMessage = nil
        do {
            let session = try await APIClient.shared.signIn(email: email, password: password)
            currentUser = session.user
            showAuthSheet = false
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func signUp(email: String, password: String, displayName: String? = nil) async {
        isLoading = true
        errorMessage = nil
        do {
            let session = try await APIClient.shared.signUp(email: email, password: password, displayName: displayName)
            currentUser = session.user
            showAuthSheet = false
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func signOut() async {
        do {
            try await APIClient.shared.signOut()
        } catch {}
        currentUser = nil
    }
}
