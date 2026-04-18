import SwiftUI

struct FilterChipsView: View {
    let title: String
    let options: [String]
    @Binding var selection: String

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(title.uppercased())
                    .font(.caption.weight(.medium))
                    .kerning(1.0)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(selection)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(options, id: \.self) { option in
                        Button(option) {
                            selection = option
                        }
                        .font(.footnote.weight(.medium))
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(selection == option ? Color.cyan.opacity(0.18) : Color.white.opacity(0.06))
                        .foregroundStyle(selection == option ? .white : .secondary)
                        .overlay(
                            Capsule()
                                .strokeBorder(selection == option ? Color.cyan.opacity(0.35) : Color.white.opacity(0.08), lineWidth: 1)
                        )
                        .clipShape(Capsule())
                    }
                }
            }
        }
    }
}
