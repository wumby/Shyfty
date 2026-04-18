import Foundation
import SwiftUI

enum SignalFormatting {
    private static let isoDateTimeFormatter = ISO8601DateFormatter()
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
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter
    }()

    static func metricLabel(_ metricName: String) -> String {
        metricName
            .replacingOccurrences(of: "_", with: " ")
            .split(separator: " ")
            .map { $0.capitalized }
            .joined(separator: " ")
    }

    static func metricLabel(for signal: Signal) -> String {
        signal.metricLabel.isEmpty ? metricLabel(signal.metricName) : signal.metricLabel
    }

    static func signalLabel(_ signalType: String) -> String {
        switch signalType {
        case "SPIKE": return "Spike"
        case "DROP": return "Drop"
        case "SHIFT": return "Shift"
        case "CONSISTENCY": return "Consistency"
        case "OUTLIER": return "Outlier"
        default: return signalType
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

    static func signalSummary(for signal: Signal) -> String {
        let label = metricLabel(for: signal)
        if let deltaPercent = deltaPercent(current: signal.currentValue, baseline: signal.baselineValue, provided: signal.movementPct) {
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

    private static func parseDate(_ value: String) -> Date? {
        if let date = isoDateTimeFormatter.date(from: value) {
            return date
        }

        return isoDateFormatter.date(from: value)
    }

    static func tint(for signalType: String) -> Color {
        switch signalType {
        case "SPIKE": return Color(red: 0.24, green: 0.82, blue: 0.56)
        case "DROP": return Color(red: 0.96, green: 0.39, blue: 0.44)
        case "SHIFT": return Color(red: 0.95, green: 0.67, blue: 0.24)
        case "CONSISTENCY": return Color(red: 0.35, green: 0.83, blue: 0.91)
        default: return Color(red: 0.86, green: 0.43, blue: 1.0)
        }
    }
}
