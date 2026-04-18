import Foundation

struct PaginatedSignals: Decodable {
    let items: [Signal]
    let hasMore: Bool
    let nextCursor: Int?

    enum CodingKeys: String, CodingKey {
        case items
        case hasMore = "has_more"
        case nextCursor = "next_cursor"
    }
}

struct ReactionSummary: Decodable, Hashable {
    let strong: Int
    let agree: Int
    let risky: Int
}

struct Signal: Identifiable, Decodable, Hashable {
    struct SummaryTemplateInputs: Decodable, Hashable {
        let currentValue: Double
        let baselineValue: Double
        let movementPct: Double?
        let baselineWindow: String
        let trendDirection: String

        enum CodingKeys: String, CodingKey {
            case currentValue = "current_value"
            case baselineValue = "baseline_value"
            case movementPct = "movement_pct"
            case baselineWindow = "baseline_window"
            case trendDirection = "trend_direction"
        }
    }

    let id: Int
    let playerID: Int
    let playerName: String
    let teamName: String
    let leagueName: String
    let signalType: String
    let metricName: String
    let currentValue: Double
    let baselineValue: Double
    let zScore: Double
    let explanation: String
    let importance: Double
    let baselineWindow: String
    let eventDate: String
    let movementPct: Double?
    let metricLabel: String
    let trendDirection: String
    let summaryTemplate: String
    let summaryTemplateInputs: SummaryTemplateInputs
    let reactionSummary: ReactionSummary
    let userReaction: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case playerID = "player_id"
        case playerName = "player_name"
        case teamName = "team_name"
        case leagueName = "league_name"
        case signalType = "signal_type"
        case metricName = "metric_name"
        case currentValue = "current_value"
        case baselineValue = "baseline_value"
        case zScore = "z_score"
        case explanation
        case importance
        case baselineWindow = "baseline_window"
        case eventDate = "event_date"
        case movementPct = "movement_pct"
        case metricLabel = "metric_label"
        case trendDirection = "trend_direction"
        case summaryTemplate = "summary_template"
        case summaryTemplateInputs = "summary_template_inputs"
        case reactionSummary = "reaction_summary"
        case userReaction = "user_reaction"
        case createdAt = "created_at"
    }
}

struct Player: Identifiable, Decodable, Hashable {
    let id: Int
    let name: String
    let position: String
    let teamName: String
    let leagueName: String
    let signalCount: Int?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case position
        case teamName = "team_name"
        case leagueName = "league_name"
        case signalCount = "signal_count"
    }
}

struct MetricSeriesPoint: Decodable, Hashable {
    let gameDate: String
    let metrics: [String: Double]

    enum CodingKeys: String, CodingKey {
        case gameDate = "game_date"
        case metrics
    }
}

struct AuthUser: Decodable, Hashable {
    let id: Int
    let email: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case createdAt = "created_at"
    }
}

struct AuthSession: Decodable {
    let user: AuthUser?
}
