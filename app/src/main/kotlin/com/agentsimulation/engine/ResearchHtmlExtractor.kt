package com.agentsimulation.engine

import android.text.Html

/**
 * Best-effort HTML extraction for public research pages.
 *
 * This is not a full browser DOM and cannot execute JavaScript.
 * It deliberately uses Android's built-in HTML decoder so no
 * additional dependency is required.
 */
object ResearchHtmlExtractor {

    fun extractTitle(html: String): String {
        val title = Regex(
            """(?is)<title\b[^>]*>(.*?)</title\s*>"""
        ).find(html)?.groupValues?.get(1).orEmpty()

        return cleanText(title).take(250)
    }

    fun extractReadableText(html: String): String {
        val withoutNoise = html
            .replace(Regex("""(?is)<!--.*?-->"""), " ")
            .replace(
                Regex(
                    """(?is)<(script|style|noscript|svg|iframe|template)\b[^>]*>.*?</\1\s*>"""
                ),
                " "
            )
            .replace(
                Regex(
                    """(?is)<(nav|header|footer|aside|form|button|dialog)\b[^>]*>.*?</\1\s*>"""
                ),
                " "
            )

        val preferred = extractPreferredRegion(withoutNoise)
        val selected = preferred.ifBlank { withoutNoise }

        val separated = selected
            .replace(
                Regex(
                    """(?i)</(p|div|article|section|h[1-6]|li|tr)\s*>"""
                ),
                "\n"
            )
            .replace(
                Regex("""(?i)<br\s*/?>"""),
                "\n"
            )

        return cleanText(separated).take(850)
    }

    fun cleanText(value: String): String {
        val decoded = try {
            Html.fromHtml(
                value,
                Html.FROM_HTML_MODE_COMPACT
            ).toString()
        } catch (_: Exception) {
            value.replace(Regex("""<[^>]*>"""), " ")
        }

        return decoded
            .replace('\u00a0', ' ')
            .replace(Regex("""[ \t]+"""), " ")
            .replace(Regex("""\s*\n\s*"""), "\n")
            .replace(Regex("""\n{3,}"""), "\n\n")
            .trim()
    }

    private fun extractPreferredRegion(html: String): String {
        val patterns = listOf(
            Regex(
                """(?is)<article\b[^>]*>(.*?)</article\s*>"""
            ),
            Regex(
                """(?is)<main\b[^>]*>(.*?)</main\s*>"""
            ),
            Regex(
                """(?is)<div\b[^>]*(?:id|class)\s*=\s*["'][^"']*(?:article|content|post|entry)[^"']*["'][^>]*>(.*?)</div\s*>"""
            )
        )

        for (pattern in patterns) {
            val match = pattern.find(html)
                ?.groupValues
                ?.getOrNull(1)

            if (!match.isNullOrBlank()) {
                val cleaned = cleanText(match)

                if (cleaned.length >= 80) {
                    return match
                }
            }
        }

        return ""
    }
}
