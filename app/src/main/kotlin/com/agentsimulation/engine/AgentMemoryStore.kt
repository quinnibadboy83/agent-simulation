
package com.agentsimulation.engine

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale
import java.util.UUID

/**
 * Persistent, device-local memory store for the Agent Simulation Engine.
 *
 * Keeps the existing SharedPreferences storage format so existing
 * saved memories remain compatible.
 *
 * Improvements:
 * - Gives the user's original messages higher relevance.
 * - Prioritises exact codes, names and phrases.
 * - Reduces noise from generic question wording.
 * - Ranks memories by relevance rather than just age.
 * - Preserves existing public memory operations.
 */
class AgentMemoryStore(context: Context) {

    data class MemoryRecord(
        val id: String,
        val content: String,
        val category: String,
        val createdAt: Long
    )

    private data class ScoredMemory(
        val memory: MemoryRecord,
        val score: Double
    )

    private val preferences = context.applicationContext
        .getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    @Synchronized
    fun save(
        content: String,
        category: String = DEFAULT_CATEGORY
    ): MemoryRecord {

        val cleanContent = content.trim()

        require(cleanContent.isNotEmpty()) {
            "Memory content cannot be empty."
        }

        val record = MemoryRecord(
            id = UUID.randomUUID().toString(),
            content = cleanContent,
            category = category.trim().ifEmpty {
                DEFAULT_CATEGORY
            },
            createdAt = System.currentTimeMillis()
        )

        val records = readRecords().toMutableList()
        records.add(record)
        writeRecords(records)

        return record
    }

    @Synchronized
    fun getAll(): List<MemoryRecord> {
        return readRecords()
            .sortedByDescending { it.createdAt }
    }

    /**
     * Search memories using relevance scoring.
     */
    @Synchronized
    fun search(query: String): List<MemoryRecord> {
        return searchRanked(query).map { it.memory }
    }

    /**
     * Search with relevance scores for diagnostics.
     */
    @Synchronized
    fun searchWithScores(
        query: String
    ): List<Pair<MemoryRecord, Double>> {

        return searchRanked(query).map {
            it.memory to it.score
        }
    }

    private fun searchRanked(query: String): List<ScoredMemory> {

        val cleanQuery = query.trim()

        if (cleanQuery.isEmpty()) {
            return readRecords()
                .sortedByDescending { it.createdAt }
                .map { ScoredMemory(it, 0.0) }
        }

        val queryTerms = tokenize(cleanQuery)
            .filterNot { it in STOP_WORDS }
            .toSet()

        if (queryTerms.isEmpty()) {
            return emptyList()
        }

        val queryPhrase = normalise(cleanQuery)

        return readRecords()
            .mapNotNull { memory ->

                val userContent = extractUserContent(
                    memory.content
                )

                val allTerms = tokenize(memory.content).toSet()
                val userTerms = tokenize(userContent).toSet()

                val matchedAll = queryTerms.intersect(allTerms)
                val matchedUser = queryTerms.intersect(userTerms)

                if (matchedAll.isEmpty()) {
                    return@mapNotNull null
                }

                val coverage = matchedAll.size.toDouble() /
                    queryTerms.size.toDouble()

                // User-authored information receives higher priority.
                val userMatchScore = matchedUser.size * 4.0

                // General content matches still contribute.
                val contentMatchScore = matchedAll.size * 1.5

                val coverageScore = coverage * 4.0

                // Exact phrase matching is particularly valuable.
                val normalisedMemory = normalise(memory.content)

                val phraseBonus = if (
                    queryPhrase.isNotEmpty() &&
                    normalisedMemory.contains(queryPhrase)
                ) {
                    8.0
                } else {
                    0.0
                }

                // Prefer matches in the original user's message.
                val userPhrase = normalise(userContent)

                val userPhraseBonus = if (
                    queryPhrase.isNotEmpty() &&
                    userPhrase.contains(queryPhrase)
                ) {
                    10.0
                } else {
                    0.0
                }

                // Small bonus for records explicitly about facts.
                val categoryBonus = if (
                    memory.category.equals(
                        "fact",
                        ignoreCase = true
                    ) ||
                    memory.category.equals(
                        "profile",
                        ignoreCase = true
                    )
                ) {
                    1.0
                } else {
                    0.0
                }

                val score =
                    userMatchScore +
                    contentMatchScore +
                    coverageScore +
                    phraseBonus +
                    userPhraseBonus +
                    categoryBonus

                ScoredMemory(memory, score)
            }
            .sortedWith(
                compareByDescending<ScoredMemory> { it.score }
                    .thenByDescending { it.memory.createdAt }
            )
    }

    /**
     * Extract the original user message from a saved conversation.
     *
     * This prevents an unrelated previous assistant response from
     * receiving the same priority as the user's own information.
     */
    private fun extractUserContent(content: String): String {

        val userMarker = "User:"
        val assistantMarker = "Assistant:"

        val userStart = content.indexOf(
            userMarker,
            ignoreCase = true
        )

        if (userStart < 0) {
            return content
        }

        val contentStart = userStart + userMarker.length

        val assistantStart = content.indexOf(
            assistantMarker,
            startIndex = contentStart,
            ignoreCase = true
        )

        return if (assistantStart >= 0) {
            content.substring(contentStart, assistantStart).trim()
        } else {
            content.substring(contentStart).trim()
        }
    }

    @Synchronized
    fun getById(id: String): MemoryRecord? {
        return readRecords().firstOrNull { it.id == id }
    }

    @Synchronized
    fun delete(id: String): Boolean {

        val records = readRecords().toMutableList()
        val removed = records.removeAll { it.id == id }

        if (removed) {
            writeRecords(records)
        }

        return removed
    }

    @Synchronized
    fun clear(): Boolean {
        return preferences.edit()
            .remove(KEY_RECORDS)
            .commit()
    }

    @Synchronized
    fun count(): Int {
        return readRecords().size
    }

    private fun tokenize(value: String): List<String> {

        return value.lowercase(Locale.ROOT)
            .split(Regex("[^\\p{L}\\p{N}_]+"))
            .filter { it.isNotBlank() }
    }

    private fun normalise(value: String): String {

        return value.lowercase(Locale.ROOT)
            .replace(Regex("[^\\p{L}\\p{N}]+"), " ")
            .trim()
    }

    private fun readRecords(): List<MemoryRecord> {

        val raw = preferences.getString(KEY_RECORDS, null)
            ?: return emptyList()

        return try {

            val array = JSONArray(raw)
            val records = mutableListOf<MemoryRecord>()

            for (index in 0 until array.length()) {

                val item = array.optJSONObject(index) ?: continue

                val id = item.optString("id")
                    .takeIf { it.isNotBlank() }
                    ?: continue

                val content = item.optString("content").trim()

                if (content.isEmpty()) continue

                records.add(
                    MemoryRecord(
                        id = id,
                        content = content,
                        category = item.optString(
                            "category",
                            DEFAULT_CATEGORY
                        ),
                        createdAt = item.optLong("createdAt", 0L)
                    )
                )
            }

            records

        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeRecords(records: List<MemoryRecord>) {

        val array = JSONArray()

        records.forEach { record ->

            array.put(
                JSONObject().apply {
                    put("id", record.id)
                    put("content", record.content)
                    put("category", record.category)
                    put("createdAt", record.createdAt)
                }
            )
        }

        check(
            preferences.edit()
                .putString(KEY_RECORDS, array.toString())
                .commit()
        ) {
            "Could not save memory to device storage."
        }
    }

    companion object {

        private const val PREFERENCES_NAME =
            "agent_persistent_memory"

        private const val KEY_RECORDS =
            "memory_records"

        private const val DEFAULT_CATEGORY =
            "general"

        private val STOP_WORDS = setOf(
            "a", "an", "and", "are", "as", "at",
            "be", "been", "but", "by", "can", "could",
            "did", "do", "does", "for", "from",
            "had", "has", "have", "how", "i", "in",
            "is", "it", "me", "my", "of", "on", "or",
            "our", "please", "tell", "that", "the",
            "their", "them", "there", "these", "they",
            "this", "to", "us", "was", "we", "were",
            "what", "when", "where", "which", "who",
            "why", "will", "with", "would", "you",
            "your", "search", "saved", "memories",
            "before", "answering", "answer", "retrieve",
            "permanently", "future", "conversation"
        )
    }
}
