import SwiftUI

/// Custom branded reaction icons — thin stroke, slightly angled for a dynamic feel.
struct ShyftReactionIcon: View {
    let reaction: ShyftReaction
    var size: CGFloat = 16

    var body: some View {
        Canvas { context, _ in
            switch reaction {
            case .shyftUp:
                drawShyftUp(context: context)
            case .shyftDown:
                drawShyftDown(context: context)
            case .shyftEye:
                drawShyftEye(context: context)
            }
        }
        .frame(width: size, height: size)
    }

    private func drawShyftUp(context: GraphicsContext) {
        var ctx = context
        // Slight counter-clockwise tilt for upward energy
        ctx.transform = CGAffineTransform(translationX: size / 2, y: size / 2)
            .rotated(by: -0.14)
            .translatedBy(x: -size / 2, y: -size / 2)

        let s = size / 24.0
        var path = Path()
        path.move(to: CGPoint(x: 5 * s, y: 17 * s))
        path.addLine(to: CGPoint(x: 12 * s, y: 6 * s))
        path.addLine(to: CGPoint(x: 19 * s, y: 17 * s))

        ctx.stroke(path, with: .foreground, style: StrokeStyle(lineWidth: 1.6 * s * (24.0 / size) * size / 16, lineCap: .round, lineJoin: .round))
    }

    private func drawShyftDown(context: GraphicsContext) {
        var ctx = context
        ctx.transform = CGAffineTransform(translationX: size / 2, y: size / 2)
            .rotated(by: 0.14)
            .translatedBy(x: -size / 2, y: -size / 2)

        let s = size / 24.0
        var path = Path()
        path.move(to: CGPoint(x: 5 * s, y: 7 * s))
        path.addLine(to: CGPoint(x: 12 * s, y: 18 * s))
        path.addLine(to: CGPoint(x: 19 * s, y: 7 * s))

        ctx.stroke(path, with: .foreground, style: StrokeStyle(lineWidth: 1.6 * s * (24.0 / size) * size / 16, lineCap: .round, lineJoin: .round))
    }

    private func drawShyftEye(context: GraphicsContext) {
        var ctx = context
        ctx.transform = CGAffineTransform(translationX: size / 2, y: size / 2)
            .rotated(by: -0.10)
            .translatedBy(x: -size / 2, y: -size / 2)

        let s = size / 24.0
        let strokeW = 1.6 * s * (24.0 / size) * size / 16

        // Almond/eye outline
        var outline = Path()
        outline.move(to: CGPoint(x: 3 * s, y: 12 * s))
        outline.addCurve(
            to: CGPoint(x: 21 * s, y: 12 * s),
            control1: CGPoint(x: 6 * s, y: 6.5 * s),
            control2: CGPoint(x: 18 * s, y: 6.5 * s)
        )
        outline.addCurve(
            to: CGPoint(x: 3 * s, y: 12 * s),
            control1: CGPoint(x: 18 * s, y: 17.5 * s),
            control2: CGPoint(x: 6 * s, y: 17.5 * s)
        )
        ctx.stroke(outline, with: .foreground, style: StrokeStyle(lineWidth: strokeW, lineCap: .round, lineJoin: .round))

        // Pupil
        let pupilR = 2.2 * s
        let pupilRect = CGRect(
            x: 12 * s - pupilR,
            y: 12 * s - pupilR,
            width: pupilR * 2,
            height: pupilR * 2
        )
        ctx.fill(Path(ellipseIn: pupilRect), with: .foreground)
    }
}
