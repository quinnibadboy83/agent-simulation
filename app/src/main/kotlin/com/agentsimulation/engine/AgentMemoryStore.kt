
package com.agentsimulation.engine

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale
import java.util.UUID

/**
 * Persistent, device-local memory store for the Agent Simulation Engine.
 *
 * Existing saved records retain the same JSON format. Search uses
 * token matching and relevance scoring rather than requiring the
 * complete query to appear verbatim in a memory.
 */
class AgentMemoryStore(context: Context) {

    data class MemoryRecord(
        val id: String,
        val content: String,
        val category: String,
        val createdAt: Long
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

        val cleanCategory = category.trim()
            .ifEmpty { DEFAULT_CATEGORY }

        val record = MemoryRecord(
            id = UUID.randomUUID().toString(),
            content = cleanContent,
            category = cleanCategory,
            createdAt = System.currentTimeMillis()
        )

        val records = readRecords().toMutableList()
        records.add(record)
        writeRecords(records)

        return record
    }

    @Synchronized
    fun getAll(): List<MemoryRecord> {
        return readRecords().sortedByDescending { it.createdAt }
    }

    /**
     * Returns memories ranked by matching query terms.
     *
     * For example, "What is my project codename?" can match a saved
     * conversation containing "My project codename is Falcon".
     */
    @Synchronized
    fun search(query: String): List<MemoryRecord> {
        val cleanQuery = query.trim()

        if (cleanQuery.isEmpty()) {
            return getAll()
        }

        val queryTerms = tokenize(cleanQuery)
            .filterNot { it in STOP_WORDS }
            .toSet()

        if (queryTerms.isEmpty()) {
            return readRecords()
                .sortedByDescending { it.createdAt }
        }

        return readRecords()
            .mapNotNull { memory ->
                val contentTerms = tokenize(memory.content).toSet()
                val categoryTerms = tokenize(memory.category).toSet()

                val matchedContentTerms = queryTerms.intersect(contentTerms)
                val matchedCategoryTerms = queryTerms.intersect(categoryTerms)

                if (
                    matchedContentTerms.isEmpty() &&
                    matchedCategoryTerms.isEmpty()
                ) {
                    return@mapNotNull null
                }

                val coverage = matchedContentTerms.size.toDouble() /
                    queryTerms.size.toDouble()

                val phraseBonus = if (
                    memory.content.contains(
                        cleanQuery,
                        ignoreCase = true
                    )
                ) {
                    3.0
                } else {
                    0.0
                }

                val categoryBonus = if (
                    matchedCategoryTerms.isNotEmpty()
                ) {
                    0.5
                } else {
                    0.0
                }

                val score = matchedContentTerms.size * 2.0 +
                    coverage * 3.0 +
                    phraseBonus +
                    categoryBonus

                ScoredMemory(memory, score)
            }
            .sortedWith(
                compareByDescending<ScoredMemory> { it.score }
                    .thenByDescending { it.memory.createdAt }
            )
            .map { it.memory }
    }

    /**
     * Search results with scores, useful for diagnosing retrieval.
     */
    @Synchronized
    fun searchWithScores(query: String): List<Pair<MemoryRecord, Double>> {
        val cleanQuery = query.trim()

        if (cleanQuery.isEmpty()) {
            return getAll().map { it to 0.0 }
        }

        val queryTerms = tokenize(cleanQuery)
            .filterNot { it in STOP_WORDS }
            .toSet()

        if (queryTerms.isEmpty()) {
            return emptyList()
        }

        return readRecords().mapNotNull { memory ->
            val contentTerms = tokenize(memory.content).toSet()
            val matchedTerms = queryTerms.intersect(contentTerms)

            if (matchedTerms.isEmpty()) {
                return@mapNotNull null
            }

            val coverage = matchedTerms.size.toDouble() /
                queryTerms.size.toDouble()

            val phraseBonus = if (
                memory.content.contains(cleanQuery, ignoreCase = true)
            ) 3.0 else 0.0

            val score = matchedTerms.size * 2.0 +
                coverage * 3.0 +
                phraseBonus

            memory to score
        }.sortedWith(
            compareByDescending<Pair<MemoryRecord, Double>> { it.second }
                .thenByDescending { it.first.createdAt }
        )
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

    private data class ScoredMemory(
        val memory: MemoryRecord,
        val score: Double
    )

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
        private const val PREFERENCES_NAME = "agent_persistent_memory"
        private const val KEY_RECORDS = "memory_records"
        private const val DEFAULT_CATEGORY = "general"

        private val STOP_WORDS = setOf(
            "a", "an", "and", "are", "as", "at", "be", "been",
            "but", "by", "can", "could", "did", "do", "does",
            "for", "from", "had", "has", "have", "how", "i",
            "in", "is", "it", "me", "my", "of", "on", "or",
            "our", "please", "tell", "that", "the", "their",
            "them", "there", "these", "they", "this", "to",
            "us", "was", "we", "were", "what", "when", "where",
            "which", "who", "why", "will", "with", "would",
            "you", "your"
        )
    }
}
