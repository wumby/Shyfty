import Foundation
import SwiftUI

enum ShyftFormatting {
    private static let isoDateTimeFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()
    private static let isoDateTimeNoFractionFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()
    private static let isoDateTimeNoZFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        return f
    }()
    private static let isoDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .iso8601)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    private static let eventDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter
    }()

    private static let eventDateShortFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "MMM d"
        return formatter
    }()

    static func metricLabel(_ metricName: String) -> String {
        metricName
            .replacingOccurrences(of: "_", with: " ")
            .split(separator: " ")
            .map { $0.capitalized }
            .joined(separator: " ")
    }

    static func metricLabel(for shyft: Shyft) -> String {
        shyft.metricLabel.isEmpty ? metricLabel(shyft.metricName) : shyft.metricLabel
    }

    static func signalLabel(_ shyftType: String) -> String {
        switch shyftType {
        case "SPIKE": return "Spike"
        case "DROP": return "Drop"
        case "SHIFT": return "Shift"
        case "OUTLIER": return "Outlier"
        default: return shyftType
        }
    }

    static func importance(for score: Double) -> String {
        if score >= 85 { return "High" }
        if score >= 65 { return "Medium" }
        return "Watch"
    }

    static func deltaPercent(current: Double, baseline: Double, provided: Double? = nil) -> Double? {
        if let provided { return provided }
        guard abs(baseline) >= 0.05 else { return nil }
        return ((current - baseline) / baseline) * 100
    }

    static func deltaText(current: Double, baseline: Double, movementPct: Double?) -> String {
        if let deltaPercent = deltaPercent(current: current, baseline: baseline, provided: movementPct) {
            let rounded = Int(deltaPercent.rounded())
            return "\(rounded >= 0 ? "+" : "")\(rounded)%"
        }

        let rawDelta = current - baseline
        return String(format: "%@%.1f", rawDelta >= 0 ? "+" : "", rawDelta)
    }

    static func movementText(metricName: String, current: Double, baseline: Double, movementPct: Double?, metricLabel: String? = nil) -> String {
        if let deltaPercent = deltaPercent(current: current, baseline: baseline, provided: movementPct) {
            let rounded = Int(abs(deltaPercent.rounded()))
            return "\(rounded)% \(deltaPercent >= 0 ? "above" : "below") baseline"
        }

        return "\(metricLabel ?? self.metricLabel(metricName)) vs baseline"
    }

    static func signalSummary(for shyft: Shyft) -> String {
        let label = metricLabel(for: shyft)
        if let deltaPercent = deltaPercent(current: shyft.currentValue, baseline: shyft.baselineValue, provided: shyft.movementPct) {
            let rounded = Int(abs(deltaPercent.rounded()))
            return "\(label) is \(rounded)% \(deltaPercent >= 0 ? "above" : "below") the recent baseline."
        }

        return "\(label) is diverging from the recent baseline."
    }

    static func relativeTime(from date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    static func relativeTime(from value: String) -> String {
        guard let date = parseDate(value) else { return value }
        return relativeTime(from: date)
    }

    static func eventDateText(_ value: String) -> String {
        guard let date = parseDate(value) else { return value }
        return eventDateFormatter.string(from: date)
    }

    static func eventDateShort(_ value: String) -> String {
        guard let date = parseDate(value) else { return value }
        return eventDateShortFormatter.string(from: date)
    }

    private static func parseDate(_ value: String) -> Date? {
        if let date = isoDateTimeFormatter.date(from: value) { return date }
        if let date = isoDateTimeNoFractionFormatter.date(from: value) { return date }
        if let date = isoDateTimeNoZFormatter.date(from: value) { return date }
        return isoDateFormatter.date(from: value)
    }

    static func tint(for shyftType: String) -> Color {
        switch shyftType {
        case "SHIFT": return Color(red: 0.60, green: 0.63, blue: 0.68)  // gray
        case "SWING": return Color(red: 0.95, green: 0.67, blue: 0.24)  // amber
        case "OUTLIER": return Color(red: 0.96, green: 0.36, blue: 0.36) // red
        default: return Color(red: 0.60, green: 0.63, blue: 0.68)
        }
    }
}
