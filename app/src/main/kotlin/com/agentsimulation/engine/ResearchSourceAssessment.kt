package com.agentsimulation.engine

import java.net.URI
import java.util.Locale

/**
 * Conservative source classification.
 *
 * These are transparent heuristics, not a fact checker.
 * A domain or provider label does not guarantee credibility.
 */
object ResearchSourceAssessment {

    fun describe(
        source: FreeResearchSource,
        allSources: List<FreeResearchSource>
    ): String {
        val host = hostOf(source.url)
        val category = classify(source, host)

        val corroboratingHosts = allSources
            .asSequence()
            .filter { it.url != source.url }
            .filter { sameTopic(source, it) }
            .map { hostOf(it.url) }
            .filter { it.isNotBlank() && it != host }
            .distinct()
            .count()

        val corroboration = when {
            corroboratingHosts >= 2 ->
                "Related results appear on at least $corroboratingHosts other distinct hosts. Check whether they independently support the same claim."

            corroboratingHosts == 1 ->
                "One related result appears on another host. Verify whether it independently supports the same claim."

            else ->
                "No independent-host corroboration was identified in this result set."
        }

        return "$category $corroboration"
    }

    private fun classify(
        source: FreeResearchSource,
        host: String
    ): String {
        val provider = source.provider.lowercase(Locale.ROOT)

        return when {
            provider.contains("arxiv") ->
                "Source class: Academic preprint repository. Abstract and metadata evidence; peer-review status is not established."

            provider.contains("github") ->
                "Source class: Software project repository. Inspect maintainers, release history, issues and code before relying on it."

            provider.contains("wikipedia") ->
                "Source class: Tertiary encyclopedia. Follow its references to locate primary sources."

            provider.contains("retrieved webpage") &&
                (host.endsWith(".gov") || host.endsWith(".gov.uk")) ->
                "Source class: Government-domain candidate. Confirm the responsible agency and page currency."

            provider.contains("retrieved webpage") &&
                (host.endsWith(".edu") || host.endsWith(".ac.uk")) ->
                "Source class: Academic-institution-domain candidate. Confirm the author, publication type and date."

            provider.contains("retrieved webpage") ->
                "Source class: Retrieved publisher webpage. Publisher and author authority have not been independently verified."

            else ->
                "Source class: Search snippet or unverified metadata. Treat as a discovery lead, not full-page evidence."
        }
    }

    private fun sameTopic(
        first: FreeResearchSource,
        second: FreeResearchSource
    ): Boolean {
        val firstTerms = terms(first.title + " " + first.summary)
        val secondTerms = terms(second.title + " " + second.summary)

        if (firstTerms.isEmpty() || secondTerms.isEmpty()) {
            return false
        }

        return firstTerms.intersect(secondTerms).size >= 2
    }

    private fun terms(value: String): Set<String> {
        return Regex("""[a-z0-9]{4,}""")
            .findAll(value.lowercase(Locale.ROOT))
            .map { it.value }
            .filterNot {
                it in setOf(
                    "that", "this", "with", "from", "have",
                    "were", "will", "their", "about", "which",
                    "evidence", "source", "retrieved"
                )
            }
            .toSet()
    }

    private fun hostOf(value: String): String {
        return try {
            URI(value).host.orEmpty()
                .lowercase(Locale.ROOT)
                .removePrefix("www.")
        } catch (_: Exception) {
            ""
        }
    }
}
