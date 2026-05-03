import Foundation

struct FeedContext: Decodable, Hashable {
    let feedMode: String
    let sortMode: String
    let personalizationReason: String?

    enum CodingKeys: String, CodingKey {
        case feedMode = "feed_mode"
        case sortMode = "sort_mode"
        case personalizationReason = "personalization_reason"
    }
}

struct PaginatedSignals: Decodable {
    let items: [FeedItem]
    let hasMore: Bool
    let nextCursor: Int?
    let feedContext: FeedContext?

    var signalItems: [Signal] {
        items.compactMap {
            if case .signal(let signal) = $0 { return signal }
            return nil
        }
    }

    enum CodingKeys: String, CodingKey {
        case items
        case hasMore = "has_more"
        case nextCursor = "next_cursor"
        case feedContext = "feed_context"
    }
}

enum FeedItem: Identifiable, Decodable, Hashable {
    case signal(Signal)
    case cascade(CascadeSignal)

    var id: String {
        switch self {
        case .signal(let signal): return "signal-\(signal.id)"
        case .cascade(let cascade): return cascade.id
        }
    }

    enum CodingKeys: String, CodingKey {
        case type
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decodeIfPresent(String.self, forKey: .type) ?? "signal"
        if type == "cascade" {
            self = .cascade(try CascadeSignal(from: decoder))
        } else {
            self = .signal(try Signal(from: decoder))
        }
    }
}

struct CascadePlayer: Decodable, Hashable {
    let id: Int?
    let name: String
}

struct CascadeTrigger: Decodable, Hashable {
    let player: CascadePlayer
    let signalID: Int
    let stat: String
    let metricLabel: String
    let delta: Double
    let deltaPercent: Double?
    let signalType: String
    let signalScore: Double

    enum CodingKeys: String, CodingKey {
        case player
        case signalID = "signal_id"
        case stat
        case metricLabel = "metric_label"
        case delta
        case deltaPercent = "delta_percent"
        case signalType = "signal_type"
        case signalScore = "signal_score"
    }
}

struct CascadeContributor: Decodable, Hashable {
    let player: CascadePlayer
    let signalID: Int
    let stat: String
    let metricLabel: String
    let delta: Double
    let deltaPercent: Double?
    let signalType: String
    let signalScore: Double

    enum CodingKeys: String, CodingKey {
        case player
        case signalID = "signal_id"
        case stat
        case metricLabel = "metric_label"
        case delta
        case deltaPercent = "delta_percent"
        case signalType = "signal_type"
        case signalScore = "signal_score"
    }
}

struct CascadeSignal: Identifiable, Decodable, Hashable {
    let id: String
    let gameID: Int
    let teamID: Int
    let team: String
    let leagueName: String
    let gameDate: String
    let createdAt: String
    let trigger: CascadeTrigger
    let contributors: [CascadeContributor]
    let underlyingSignals: [Signal]
    let narrativeSummary: String?

    enum CodingKeys: String, CodingKey {
        case id
        case gameID = "game_id"
        case teamID = "team_id"
        case team
        case leagueName = "league_name"
        case gameDate = "game_date"
        case createdAt = "created_at"
        case trigger
        case contributors
        case underlyingSignals = "underlying_signals"
        case narrativeSummary = "narrative_summary"
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
    let subjectType: String?
    let playerID: Int?
    let teamID: Int
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
    let commentCount: Int
    let opponent: String?
    let homeAway: String?
    let gameResult: String?
    let finalScore: String?
    let streak: Int
    let classificationReason: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case subjectType = "subject_type"
        case playerID = "player_id"
        case teamID = "team_id"
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
        case commentCount = "comment_count"
        case opponent
        case homeAway = "home_away"
        case gameResult = "game_result"
        case finalScore = "final_score"
        case streak
        case classificationReason = "classification_reason"
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
    let isFollowed: Bool
    let recentBoxScores: [PlayerBoxScore]?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case position
        case teamName = "team_name"
        case leagueName = "league_name"
        case signalCount = "signal_count"
        case isFollowed = "is_followed"
        case recentBoxScores = "recent_box_scores"
    }
}

struct PlayerBoxScore: Decodable, Hashable, Identifiable {
    let gameID: Int
    let gameDate: String
    let season: String?
    let opponent: String
    let homeAway: String
    let points: Int?
    let rebounds: Int?
    let assists: Int?
    let passingYards: Int?
    let rushingYards: Int?
    let receivingYards: Int?
    let touchdowns: Int?
    let usageRate: Double?
    let steals: Int?
    let blocks: Int?
    let turnovers: Int?
    let minutesPlayed: Double?
    let plusMinus: Int?
    let fgPct: Double?
    let fg3Pct: Double?
    let ftPct: Double?

    var id: Int { gameID }

    enum CodingKeys: String, CodingKey {
        case gameID = "game_id"
        case gameDate = "game_date"
        case season
        case opponent
        case homeAway = "home_away"
        case points
        case rebounds
        case assists
        case passingYards = "passing_yards"
        case rushingYards = "rushing_yards"
        case receivingYards = "receiving_yards"
        case touchdowns
        case usageRate = "usage_rate"
        case steals
        case blocks
        case turnovers
        case minutesPlayed = "minutes_played"
        case plusMinus = "plus_minus"
        case fgPct = "fg_pct"
        case fg3Pct = "fg3_pct"
        case ftPct = "ft_pct"
    }
}

struct Team: Identifiable, Decodable, Hashable {
    let id: Int
    let name: String
    let leagueName: String
    let playerCount: Int
    let signalCount: Int?
    let isFollowed: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case leagueName = "league_name"
        case playerCount = "player_count"
        case signalCount = "signal_count"
        case isFollowed = "is_followed"
    }
}

struct TeamDetail: Decodable, Hashable {
    let id: Int
    let name: String
    let leagueName: String
    let playerCount: Int
    let signalCount: Int?
    let isFollowed: Bool
    let players: [Player]
    let recentSignals: [Signal]
    let recentBoxScores: [TeamBoxScore]

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case leagueName = "league_name"
        case playerCount = "player_count"
        case signalCount = "signal_count"
        case isFollowed = "is_followed"
        case players
        case recentSignals = "recent_signals"
        case recentBoxScores = "recent_box_scores"
    }
}

struct TeamBoxScore: Decodable, Hashable, Identifiable {
    let gameID: Int
    let gameDate: String
    let season: String?
    let opponent: String
    let homeAway: String
    let points: Int?
    let rebounds: Int?
    let assists: Int?
    let fgPct: Double?
    let fg3Pct: Double?
    let turnovers: Int?
    let pace: Double?
    let offRating: Double?

    var id: Int { gameID }

    enum CodingKeys: String, CodingKey {
        case gameID = "game_id"
        case gameDate = "game_date"
        case season
        case opponent
        case homeAway = "home_away"
        case points
        case rebounds
        case assists
        case fgPct = "fg_pct"
        case fg3Pct = "fg3_pct"
        case turnovers
        case pace
        case offRating = "off_rating"
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

struct Comment: Decodable, Identifiable, Hashable {
    let id: Int
    let signalID: Int
    let userID: Int
    let userEmail: String
    let body: String
    let createdAt: String
    let updatedAt: String
    let isEdited: Bool
    let canEdit: Bool
    let canDelete: Bool
    let canReport: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case signalID = "signal_id"
        case userID = "user_id"
        case userEmail = "user_email"
        case body
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case isEdited = "is_edited"
        case canEdit = "can_edit"
        case canDelete = "can_delete"
        case canReport = "can_report"
    }
}

struct ProfilePreferences: Decodable, Hashable {
    let preferredLeague: String?
    let preferredSignalType: String?
    let defaultSortMode: String
    let defaultFeedMode: String
    let notificationReleases: Bool
    let notificationDigest: Bool

    enum CodingKeys: String, CodingKey {
        case preferredLeague = "preferred_league"
        case preferredSignalType = "preferred_signal_type"
        case defaultSortMode = "default_sort_mode"
        case defaultFeedMode = "default_feed_mode"
        case notificationReleases = "notification_releases"
        case notificationDigest = "notification_digest"
    }
}

struct UserProfile: Decodable {
    struct Follows: Decodable, Hashable {
        let players: [Int]
        let teams: [Int]
    }

    let preferences: ProfilePreferences
    let follows: Follows

    enum CodingKeys: String, CodingKey {
        case preferences
        case follows
    }
}

// MARK: - Signal Detail (Trace)

struct BaselineSample: Decodable, Identifiable {
    var id: Int { statId }
    let statId: Int
    let gameDate: String
    let value: Double

    enum CodingKeys: String, CodingKey {
        case statId = "stat_id"
        case gameDate = "game_date"
        case value
    }
}

struct RollingMetricTrace: Decodable {
    let rollingAvg: Double
    let rollingStddev: Double
    let zScore: Double

    enum CodingKeys: String, CodingKey {
        case rollingAvg = "rolling_avg"
        case rollingStddev = "rolling_stddev"
        case zScore = "z_score"
    }
}

struct SourceStatContext: Decodable {
    let gameDate: String
    let currentValue: Double
    let rawStats: [String: Double]

    enum CodingKeys: String, CodingKey {
        case gameDate = "game_date"
        case currentValue = "current_value"
        case rawStats = "raw_stats"
    }
}

struct SignalTrace: Decodable {
    let signal: Signal
    let rollingMetric: RollingMetricTrace?
    let sourceStat: SourceStatContext?
    let baselineSamples: [BaselineSample]
    let discussionPreview: [Comment]
    let feedContext: FeedContext?

    enum CodingKeys: String, CodingKey {
        case signal
        case rollingMetric = "rolling_metric"
        case sourceStat = "source_stat"
        case baselineSamples = "baseline_samples"
        case discussionPreview = "discussion_preview"
        case feedContext = "feed_context"
    }
}

// MARK: - Ingest Status

struct IngestRun: Decodable, Hashable {
    let startedAt: String
    let finishedAt: String?
    let status: String
    let durationSeconds: Double?
    let errorMessage: String?

    enum CodingKeys: String, CodingKey {
        case startedAt = "started_at"
        case finishedAt = "finished_at"
        case status
        case durationSeconds = "duration_seconds"
        case errorMessage = "error_message"
    }
}

struct IngestStatus: Decodable {
    let status: String
    let lastUpdated: String?
    let startedAt: String?
    let finishedAt: String?
    let currentRunDurationSeconds: Double?
    let lastError: String?
    let recentRuns: [IngestRun]

    enum CodingKeys: String, CodingKey {
        case status
        case lastUpdated = "last_updated"
        case startedAt = "started_at"
        case finishedAt = "finished_at"
        case currentRunDurationSeconds = "current_run_duration_seconds"
        case lastError = "last_error"
        case recentRuns = "recent_runs"
    }
}

// MARK: - Feed Grouping

struct GroupedSignal: Identifiable {
    let id: String
    let signals: [Signal]  // sorted by importance descending

    var primarySignal: Signal { signals[0] }
}
