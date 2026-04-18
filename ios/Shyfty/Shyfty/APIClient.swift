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

    func fetchSignals(league: String? = nil, signalType: String? = nil, player: String? = nil) async throws -> [Signal] {
        var components = URLComponents(url: baseURL.appendingPathComponent("signals"), resolvingAgainstBaseURL: false)!
        components.queryItems = [
            league.map { URLQueryItem(name: "league", value: $0) },
            signalType.map { URLQueryItem(name: "signal_type", value: $0) },
            player.map { URLQueryItem(name: "player", value: $0) },
            URLQueryItem(name: "limit", value: "50")
        ].compactMap { $0 }
        let paginated: PaginatedSignals = try await get(components.url!)
        return paginated.items
    }

    func fetchTrendingSignals() async throws -> [Signal] {
        let url = baseURL.appendingPathComponent("signals/trending").appending(queryItems: [
            URLQueryItem(name: "limit", value: "12")
        ])
        return try await get(url)
    }

    func fetchSignalDetail(id: Int) async throws -> SignalTrace {
        return try await get(baseURL.appendingPathComponent("signals/\(id)"))
    }

    // MARK: - Players

    func fetchPlayer(id: Int) async throws -> Player {
        return try await get(baseURL.appendingPathComponent("players/\(id)"))
    }

    func followPlayer(id: Int) async throws {
        let _: EmptyResponse = try await post(baseURL.appendingPathComponent("players/\(id)/follow"), body: EmptyBody())
    }

    func unfollowPlayer(id: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("players/\(id)/follow"))
        request.httpMethod = "DELETE"
        let (_, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: Data())
    }

    func fetchPlayerSignals(id: Int) async throws -> [Signal] {
        return try await get(baseURL.appendingPathComponent("players/\(id)/signals"))
    }

    func fetchPlayerMetrics(id: Int) async throws -> [MetricSeriesPoint] {
        return try await get(baseURL.appendingPathComponent("players/\(id)/metrics"))
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

    func signUp(email: String, password: String) async throws -> AuthSession {
        let body = ["email": email, "password": password]
        return try await post(baseURL.appendingPathComponent("auth/signup"), body: body)
    }

    func signOut() async throws {
        let _: EmptyResponse = try await post(baseURL.appendingPathComponent("auth/signout"), body: EmptyBody())
    }

    // MARK: - Reactions

    func setReaction(signalId: Int, type: String) async throws {
        let body = ["type": type]
        let _: EmptyResponse = try await put(baseURL.appendingPathComponent("signals/\(signalId)/reaction"), body: body)
    }

    func clearReaction(signalId: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("signals/\(signalId)/reaction"))
        request.httpMethod = "DELETE"
        let (_, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: Data())
    }

    // MARK: - Favorites

    func addFavorite(signalId: Int) async throws {
        let _: EmptyResponse = try await post(baseURL.appendingPathComponent("favorites/\(signalId)"), body: EmptyBody())
    }

    func removeFavorite(signalId: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("favorites/\(signalId)"))
        request.httpMethod = "DELETE"
        let (_, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: Data())
    }

    func fetchFavorites() async throws -> [Signal] {
        let paginated: PaginatedSignals = try await get(baseURL.appendingPathComponent("favorites"))
        return paginated.items
    }

    // MARK: - Comments

    func fetchComments(signalId: Int) async throws -> [Comment] {
        try await get(baseURL.appendingPathComponent("signals/\(signalId)/comments"))
    }

    func postComment(signalId: Int, body: String) async throws -> Comment {
        try await post(baseURL.appendingPathComponent("signals/\(signalId)/comments"), body: ["body": body])
    }

    func updateComment(commentId: Int, body: String) async throws -> Comment {
        try await put(baseURL.appendingPathComponent("comments/\(commentId)"), body: ["body": body])
    }

    func deleteComment(commentId: Int) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("comments/\(commentId)"))
        request.httpMethod = "DELETE"
        let (_, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: Data())
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
        request.httpBody = try JSONEncoder().encode(body)
        let (data, response) = try await session.data(for: request)
        _ = try validateResponse(response, data: data)
        if data.isEmpty { return EmptyResponse() as! T }
        return try decoder.decode(T.self, from: data)
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
            preconditionFailure("Missing ShyftyAPIBaseURL in Info.plist for physical-device builds. Run scripts/start-dev.sh to refresh the local debug host config.")
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
