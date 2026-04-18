import SwiftUI

@main
struct ShyftyApp: App {
    @StateObject private var auth = AuthViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(auth)
                .task {
                    await auth.refreshSession()
                }
        }
    }
}

