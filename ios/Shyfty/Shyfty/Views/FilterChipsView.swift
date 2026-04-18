import SwiftUI

struct FilterChipsView: View {
    let title: String
    let options: [String]
    @Binding var selection: String

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(title.uppercased())
                    .shyftyEyebrow()
                Spacer()
                Text(selection)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(ShyftyTheme.muted)
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(options, id: \.self) { option in
                        Button(option) {
                            selection = option
                        }
                        .buttonStyle(ShyftyPillButtonStyle(active: selection == option))
                    }
                }
            }
            .scrollIndicators(.hidden)
        }
    }
}
