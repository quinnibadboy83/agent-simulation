
package com.agentsimulation.engine

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/**
 * Persistent, device-local memory store for the Agent Simulation Engine.
 *
 * Records survive application restarts and are stored in private
 * application preferences. This class does not send memory to the network.
 *
 * All public operations are synchronised so multiple callers cannot
 * overwrite one another's updates.
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

    @Synchronized
    fun search(query: String): List<MemoryRecord> {
        val cleanQuery = query.trim()

        if (cleanQuery.isEmpty()) {
            return getAll()
        }

        return readRecords()
            .filter {
                it.content.contains(cleanQuery, ignoreCase = true) ||
                    it.category.contains(cleanQuery, ignoreCase = true)
            }
            .sortedByDescending { it.createdAt }
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

    private fun readRecords(): List<MemoryRecord> {
        val raw = preferences.getString(KEY_RECORDS, null)
            ?: return emptyList()

        return try {
            val array = JSONArray(raw)
            val records = mutableListOf<MemoryRecord>()

            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue
                val id = item.optString("id").takeIf { it.isNotBlank() }
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
    }
}
