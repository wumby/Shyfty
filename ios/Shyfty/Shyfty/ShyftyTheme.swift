import SwiftUI

enum ShyftyTheme {
    static let bg = Color(red: 7 / 255, green: 17 / 255, blue: 31 / 255)
    static let bgDeep = Color(red: 5 / 255, green: 13 / 255, blue: 25 / 255)
    static let panel = Color(red: 10 / 255, green: 23 / 255, blue: 41 / 255).opacity(0.78)
    static let panelStrong = Color(red: 7 / 255, green: 17 / 255, blue: 31 / 255).opacity(0.94)
    static let border = Color(red: 135 / 255, green: 166 / 255, blue: 201 / 255).opacity(0.16)
    static let borderStrong = Color(red: 166 / 255, green: 194 / 255, blue: 225 / 255).opacity(0.30)
    static let accent = Color(red: 249 / 255, green: 115 / 255, blue: 22 / 255)
    static let accentSoft = Color(red: 249 / 255, green: 115 / 255, blue: 22 / 255).opacity(0.16)
    static let ink = Color(red: 246 / 255, green: 242 / 255, blue: 232 / 255)
    static let muted = Color(red: 139 / 255, green: 160 / 255, blue: 185 / 255)
    static let success = Color(red: 52 / 255, green: 211 / 255, blue: 153 / 255)
    static let danger = Color(red: 251 / 255, green: 113 / 255, blue: 133 / 255)
    static let warning = Color(red: 251 / 255, green: 191 / 255, blue: 36 / 255)
    static let spotlightBlue = Color(red: 56 / 255, green: 189 / 255, blue: 248 / 255).opacity(0.16)

    static let screenBackground = LinearGradient(
        colors: [Color(red: 8 / 255, green: 19 / 255, blue: 37 / 255), bg, bgDeep],
        startPoint: .top,
        endPoint: .bottom
    )

    static let panelGradient = LinearGradient(
        colors: [Color.white.opacity(0.06), Color.white.opacity(0.025)],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let cardGradient = LinearGradient(
        colors: [Color.white.opacity(0.07), Color.white.opacity(0.04)],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

struct ShyftyBackground: View {
    var body: some View {
        ZStack {
            ShyftyTheme.screenBackground
            RadialGradient(colors: [ShyftyTheme.accent.opacity(0.16), .clear], center: .topLeading, startRadius: 0, endRadius: 260)
                .offset(x: -40, y: -80)
            RadialGradient(colors: [ShyftyTheme.spotlightBlue, .clear], center: .topTrailing, startRadius: 0, endRadius: 260)
                .offset(x: 30, y: -90)
        }
        .ignoresSafeArea()
    }
}

struct ShyftyFrameModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(
                RoundedRectangle(cornerRadius: 30, style: .continuous)
                    .fill(ShyftyTheme.panel)
                    .overlay(
                        RoundedRectangle(cornerRadius: 30, style: .continuous)
                            .strokeBorder(ShyftyTheme.border, lineWidth: 1)
                    )
                    .overlay(alignment: .topLeading) {
                        LinearGradient(
                            colors: [Color.white.opacity(0.07), .clear, ShyftyTheme.accent.opacity(0.10)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 30, style: .continuous))
                    }
                    .shadow(color: .black.opacity(0.30), radius: 30, y: 18)
            )
    }
}

struct ShyftyPanelModifier: ViewModifier {
    let strong: Bool

    func body(content: Content) -> some View {
        content
            .background(
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(strong ? ShyftyTheme.panelStrong : ShyftyTheme.panel)
                    .overlay(
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .strokeBorder(strong ? ShyftyTheme.borderStrong : ShyftyTheme.border, lineWidth: 1)
                    )
                    .overlay {
                        if !strong {
                            ShyftyTheme.panelGradient
                                .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
                        }
                    }
                    .shadow(color: Color.black.opacity(0.24), radius: 24, y: 12)
            )
    }
}

extension View {
    func shyftyFrame() -> some View {
        modifier(ShyftyFrameModifier())
    }

    func shyftyPanel(strong: Bool = false) -> some View {
        modifier(ShyftyPanelModifier(strong: strong))
    }

    func shyftyHeadline(_ size: CGFloat) -> some View {
        font(.system(size: size, weight: .semibold, design: .serif))
            .foregroundStyle(ShyftyTheme.ink)
    }

    func shyftyEyebrow() -> some View {
        font(.system(size: 10, weight: .semibold))
            .tracking(3.4)
            .textCase(.uppercase)
            .foregroundStyle(ShyftyTheme.muted)
    }

    func shyftyField() -> some View {
        padding(.horizontal, 18)
            .padding(.vertical, 14)
            .background(Color.white.opacity(0.04))
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .strokeBorder(ShyftyTheme.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
            .foregroundStyle(ShyftyTheme.ink)
    }
}

struct ShyftyAccentDot: View {
    var body: some View {
        Circle()
            .fill(ShyftyTheme.accent)
            .frame(width: 8, height: 8)
            .shadow(color: ShyftyTheme.accent.opacity(0.7), radius: 8)
    }
}

struct ShyftyPillButtonStyle: ButtonStyle {
    var active: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 11, weight: .semibold))
            .tracking(1.8)
            .textCase(.uppercase)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .foregroundStyle(active ? Color(red: 1.0, green: 0.85, blue: 0.74) : (configuration.isPressed ? ShyftyTheme.ink : ShyftyTheme.muted))
            .background(active ? ShyftyTheme.accentSoft : Color.white.opacity(configuration.isPressed ? 0.06 : 0.03))
            .overlay(
                Capsule()
                    .strokeBorder(active ? ShyftyTheme.accent.opacity(0.4) : ShyftyTheme.border, lineWidth: 1)
            )
            .clipShape(Capsule())
    }
}
