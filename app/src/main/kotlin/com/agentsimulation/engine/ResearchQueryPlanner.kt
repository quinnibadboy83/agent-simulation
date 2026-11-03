package com.agentsimulation.engine

import java.util.Locale

data class ResearchQueryPlan(
    val githubOnly: Boolean,
    val shouldSearchGitHub: Boolean,
    val shouldSearchArxiv: Boolean,
    val searchTerms: String
)

/**
 * Plans supplementary provider searches without making GitHub
 * or academic search the default for ordinary questions.
 */
object ResearchQueryPlanner {

    private val stopWords = setOf(
        "a", "an", "and", "are", "as", "at", "be", "before",
        "by", "can", "could", "did", "do", "does", "for",
        "from", "get", "give", "has", "have", "how", "i",
        "in", "into", "is", "it", "latest", "me", "my",
        "of", "on", "or", "our", "please", "research",
        "show", "tell", "that", "the", "their", "them",
        "these", "this", "those", "to", "using", "use",
        "was", "we", "what", "when", "where", "which",
        "who", "why", "will", "with", "would", "you", "your"
    )

    private val githubPattern = Regex(
        """\b(github|repository|repositories|repo|repos|source code|open source|software project|project|projects|library|libraries|sdk|implementation|codebase)\b"""
    )

    private val technicalPattern = Regex(
        """\b(llama\.cpp|gguf|llm|language model|android inference|machine learning|artificial intelligence|neural network|model training|model quantization|transformer|on-device ai|edge ai)\b"""
    )

    private val scientificPattern = Regex(
        """\b(scientific|science|paper|papers|study|studies|academic|arxiv|peer reviewed|research paper|journal article)\b"""
    )

    fun plan(query: String): ResearchQueryPlan {
        val normalized = query.lowercase(Locale.ROOT)

        val githubOnly = Regex(
            """\b(only\s+(search|use)\s+github|github\s+only)\b"""
        ).containsMatchIn(normalized)

        val technical = technicalPattern.containsMatchIn(normalized)
        val scientific = scientificPattern.containsMatchIn(normalized)
        val githubRequested = githubPattern.containsMatchIn(normalized)

        val terms = Regex(
            """[a-zA-Z0-9][a-zA-Z0-9.+#_-]*"""
        ).findAll(normalized)
            .map { it.value }
            .filter { it !in stopWords && it.length > 1 }
            .distinct()
            .take(10)
            .joinToString(" ")

        return ResearchQueryPlan(
            githubOnly = githubOnly,
            shouldSearchGitHub = githubRequested || technical,
            shouldSearchArxiv = technical || scientific,
            searchTerms = terms.ifBlank { query.trim() }
        )
    }
}
