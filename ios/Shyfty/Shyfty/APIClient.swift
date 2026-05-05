import Foundation

enum APIError: LocalizedError {
    case httpError(Int, String)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .httpError(let code, let message): return "HTTP \(code): \(message)"
        case .decodingError(let error): return "Decode error: \(error.localizedDescription)"
        }
    }
}

final class APIClient {
    static let shared = APIClient()
    private static let csrfCookieName = "shyfty_csrf"
    private static let csrfHeaderName = "X-CSRF-Token"

    private let decoder: JSONDecoder
    private let baseURL: URL
    private let session: URLSession

    private init() {
        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        baseURL = Self.resolveBaseURL()

        let config = URLSessionConfiguration.default
        config.httpCookieAcceptPolicy = .always
        config.httpShouldSetCookies = true
        session = URLSession(configuration: config)
    }

    // MARK: - Signals

    func fetchShyfts(league: String? = nil, shyftType: String? = nil, player: String? = nil, feed: String? = nil, cursor: Int? = nil) async throws -> PaginatedShyfts {
        var components = URLComponents(url: baseURL.appendingPathComponent("shyfts"), resolvingAgainstBaseURL: false)!
        components.queryItems = [
            league.map { URLQueryItem(name: "league", value: $0) },
            shyftType.map { URLQueryItem(name: "shyft_type", value: $0) },
            player.map { URLQueryItem(name: "player", value: $0) },
            feed.map { URLQueryItem(name: "feed", value: $0) },
            cursor.map { URLQueryItem(name: "before_id", value: String($0)) },
            URLQueryItem(name: "limit", value: "30"),
        ].compactMap { $0 }
        return try await get(components.url!)
    }

    func fetchTrendingShyfts() async throws -> [Shyft] {
        let url = baseURL.appendingPathComponent("shyfts/trending").appending(queryItems: [
            URLQueryItem(name: "limit", value: "12")
        ])
        return try await get(url)
    }

    func fetchShyftDetail(id: Int) async throws -> ShyftTrace {
        return try await get(baseURL.appendingPathComponent("shyfts/\(id)"))
    }

    // MARK: - Players

    func fetchPlayers() async throws -> [Player] {
        return try await get(baseURL.appendingPathComponent("players"))
    }

    func fetchPlayer(id: Int) async throws -> Player {
        return try await get(baseURL.appendingPathComponent("players/\(id)"))
    }

    func followPlayer(id: Int) async throws {
        let _: EmptyResponse = try await post(baseURL.appendingPathComponent("players/\(id)/follow"), body: EmptyBody())
    }

    func unfollowPlayer(id: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("players/\(id)/follow"))
        request.httpMethod = "DELETE"
        try attachCSRFToken(to: &request)
        let (data, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: data)
    }

    func fetchPlayerShyfts(id: Int) async throws -> [Shyft] {
        return try await get(baseURL.appendingPathComponent("players/\(id)/shyfts"))
    }

    func fetchPlayerMetrics(id: Int) async throws -> [MetricSeriesPoint] {
        return try await get(baseURL.appendingPathComponent("players/\(id)/metrics"))
    }

    // MARK: - Teams

    func fetchTeams() async throws -> [Team] {
        try await get(baseURL.appendingPathComponent("teams"))
    }

    func followTeam(id: Int) async throws {
        let _: EmptyResponse = try await post(baseURL.appendingPathComponent("teams/\(id)/follow"), body: EmptyBody())
    }

    func unfollowTeam(id: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("teams/\(id)/follow"))
        request.httpMethod = "DELETE"
        try attachCSRFToken(to: &request)
        let (data, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: data)
    }

    func fetchTeam(id: Int) async throws -> TeamDetail {
        try await get(baseURL.appendingPathComponent("teams/\(id)"))
    }

    // MARK: - Auth

    func fetchSession() async throws -> AuthSession {
        return try await get(baseURL.appendingPathComponent("auth/me"))
    }

    func signIn(email: String, password: String) async throws -> AuthSession {
        let body = ["email": email, "password": password]
        return try await post(baseURL.appendingPathComponent("auth/signin"), body: body)
    }

    func signUp(email: String, password: String, displayName: String? = nil) async throws -> AuthSession {
        struct SignUpPayload: Encodable {
            let email: String
            let password: String
            let display_name: String?
        }
        let payload = SignUpPayload(
            email: email,
            password: password,
            display_name: displayName?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
                ? displayName?.trimmingCharacters(in: .whitespacesAndNewlines)
                : nil
        )
        return try await post(baseURL.appendingPathComponent("auth/signup"), body: payload)
    }

    func signOut() async throws {
        let _: EmptyResponse = try await post(baseURL.appendingPathComponent("auth/signout"), body: EmptyBody())
    }

    func changePassword(currentPassword: String, newPassword: String, confirmNewPassword: String) async throws -> String {
        struct PasswordChangePayload: Encodable {
            let current_password: String
            let new_password: String
            let confirm_new_password: String
        }
        struct MessageResponse: Decodable {
            let message: String
        }

        let payload = PasswordChangePayload(
            current_password: currentPassword,
            new_password: newPassword,
            confirm_new_password: confirmNewPassword
        )
        let response: MessageResponse = try await put(baseURL.appendingPathComponent("auth/password"), body: payload)
        return response.message
    }

    // MARK: - Reactions

    func setReaction(shyftId: Int, type: ShyftReaction) async throws {
        let body = ["type": type.rawValue]
        let _: EmptyResponse = try await put(baseURL.appendingPathComponent("shyfts/\(shyftId)/reaction"), body: body)
    }

    func clearReaction(shyftId: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("shyfts/\(shyftId)/reaction"))
        request.httpMethod = "DELETE"
        try attachCSRFToken(to: &request)
        let (data, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: data)
    }

    // MARK: - Comments

    func fetchComments(shyftId: Int) async throws -> [Comment] {
        try await get(baseURL.appendingPathComponent("shyfts/\(shyftId)/comments"))
    }

    func postComment(shyftId: Int, body: String) async throws -> Comment {
        try await post(baseURL.appendingPathComponent("shyfts/\(shyftId)/comments"), body: ["body": body])
    }

    func updateComment(commentId: Int, body: String) async throws -> Comment {
        try await put(baseURL.appendingPathComponent("comments/\(commentId)"), body: ["body": body])
    }

    func deleteComment(commentId: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("comments/\(commentId)"))
        request.httpMethod = "DELETE"
        try attachCSRFToken(to: &request)
        let (data, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: data)
    }

    func reportComment(commentId: Int) async throws {
        let _: EmptyResponse = try await post(baseURL.appendingPathComponent("comments/\(commentId)/report"), body: ["reason": "abuse"])
    }

    // MARK: - Profile

    func fetchProfile() async throws -> UserProfile {
        try await get(baseURL.appendingPathComponent("profile"))
    }

    func updatePreferences(payload: [String: AnyEncodable]) async throws -> ProfilePreferences {
        try await put(baseURL.appendingPathComponent("profile/preferences"), body: payload)
    }

    func updateProfile(displayName: String?) async throws -> UserProfile {
        struct ProfilePayload: Encodable {
            let display_name: String?
        }
        let clean = displayName?.trimmingCharacters(in: .whitespacesAndNewlines)
        return try await put(
            baseURL.appendingPathComponent("profile"),
            body: ProfilePayload(display_name: (clean?.isEmpty == false) ? clean : "")
        )
    }

    // MARK: - Ingest

    func fetchIngestStatus() async throws -> IngestStatus {
        return try await get(baseURL.appendingPathComponent("ingest/status"))
    }

    // MARK: - Helpers

    private struct EmptyBody: Encodable {}
    private struct EmptyResponse: Decodable {}
    struct AnyEncodable: Encodable {
        private let encodeImpl: (Encoder) throws -> Void

        init<T: Encodable>(_ value: T) {
            self.encodeImpl = value.encode
        }

        func encode(to encoder: Encoder) throws {
            try encodeImpl(encoder)
        }
    }

    private func get<T: Decodable>(_ url: URL) async throws -> T {
        let (data, response) = try await session.data(from: url)
        _ = try validateResponse(response, data: data)
        return try decoder.decode(T.self, from: data)
    }

    private func post<Body: Encodable, T: Decodable>(_ url: URL, body: Body) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        try attachCSRFToken(to: &request)
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: data)
        if data.isEmpty { return EmptyResponse() as! T }
        return try decoder.decode(T.self, from: data)
    }

    private func put<Body: Encodable, T: Decodable>(_ url: URL, body: Body) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        try attachCSRFToken(to: &request)
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: data)
        if data.isEmpty { return EmptyResponse() as! T }
        return try decoder.decode(T.self, from: data)
    }

    private func attachCSRFToken(to request: inout URLRequest) throws {
        guard let url = request.url else { return }
        let cookies = session.configuration.httpCookieStorage?.cookies(for: url) ?? HTTPCookieStorage.shared.cookies(for: url) ?? []
        if let token = cookies.first(where: { $0.name == Self.csrfCookieName })?.value {
            request.setValue(token, forHTTPHeaderField: Self.csrfHeaderName)
        }
    }

    @discardableResult
    private func validateResponse(_ response: URLResponse, data: Data) throws -> HTTPURLResponse {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.httpError(0, "No HTTP response")
        }
        guard (200..<300).contains(http.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.httpError(http.statusCode, message)
        }
        return http
    }

    private static func resolveBaseURL() -> URL {
#if targetEnvironment(simulator)
        return URL(string: "http://127.0.0.1:8001/api/")!
#else
        guard
            let configuredBaseURL = Bundle.main.object(forInfoDictionaryKey: "ShyftyAPIBaseURL") as? String,
            let baseURL = URL(string: configuredBaseURL),
            !configuredBaseURL.isEmpty
        else {
            preconditionFailure("Missing ShyftyAPIBaseURL in Info.plist for physical-device builds. Run scripts/reset-dev.sh to refresh the local debug host config.")
        }
        return baseURL
#endif
    }
}

private extension URL {
    func appending(queryItems: [URLQueryItem]) -> URL {
        var components = URLComponents(url: self, resolvingAgainstBaseURL: false)!
        components.queryItems = (components.queryItems ?? []) + queryItems
        return components.url!
    }
}
