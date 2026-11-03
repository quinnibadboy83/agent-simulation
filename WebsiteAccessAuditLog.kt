package com.agentsimulation.engine

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/**
 * Device-local audit history for website access decisions.
 *
 * Never pass passwords, API tokens, cookies, session IDs or other
 * authentication material into the detail parameter.
 */
class WebsiteAccessAuditLog(context: Context) {

    private val preferences = context.applicationContext
        .getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    @Synchronized
    fun record(
        siteId: String,
        action: String,
        outcome: String,
        detail: String = ""
    ): WebsiteAuditEvent {
        require(siteId.isNotBlank()) {
            "Website ID cannot be empty."
        }

        val safeAction = action
            .take(MAX_LABEL_LENGTH)
            .ifBlank { "UNKNOWN" }

        val safeOutcome = outcome
            .take(MAX_LABEL_LENGTH)
            .ifBlank { "UNKNOWN" }

        val safeDetail = redact(detail)
            .take(MAX_DETAIL_LENGTH)

        val event = WebsiteAuditEvent(
            eventId = UUID.randomUUID().toString(),
            siteId = siteId,
            action = safeAction,
            outcome = safeOutcome,
            detail = safeDetail,
            timestamp = System.currentTimeMillis()
        )

        val events = readEvents().toMutableList()
        events.add(event)

        writeEvents(
            events.takeLast(MAX_EVENTS)
        )

        return event
    }

    @Synchronized
    fun getRecent(limit: Int = 100): List<WebsiteAuditEvent> {
        val safeLimit = limit.coerceIn(1, MAX_EVENTS)

        return readEvents()
            .sortedByDescending { it.timestamp }
            .take(safeLimit)
    }

    @Synchronized
    fun getForWebsite(
        siteId: String,
        limit: Int = 100
    ): List<WebsiteAuditEvent> {
        val safeLimit = limit.coerceIn(1, MAX_EVENTS)

        return readEvents()
            .filter { it.siteId == siteId }
            .sortedByDescending { it.timestamp }
            .take(safeLimit)
    }

    @Synchronized
    fun count(): Int = readEvents().size

    @Synchronized
    fun clear(): Boolean {
        return preferences.edit()
            .remove(KEY_EVENTS)
            .commit()
    }

    private fun redact(value: String): String {
        var result = value

        val sensitivePatterns = listOf(
            Regex(
                "(?i)(password|passwd|token|api[_-]?key|secret|cookie|authorization)\\s*[:=]\\s*[^\\s,;]+"
            ),
            Regex(
                "(?i)bearer\\s+[A-Za-z0-9._~+/=-]+"
            )
        )

        sensitivePatterns.forEach { pattern ->
            result = result.replace(pattern) {
                "[REDACTED]"
            }
        }

        return result
    }

    private fun readEvents(): List<WebsiteAuditEvent> {
        val raw = preferences.getString(KEY_EVENTS, null)
            ?: return emptyList()

        return try {
            val array = JSONArray(raw)
            val events = mutableListOf<WebsiteAuditEvent>()

            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue

                val event = runCatching {
                    WebsiteAuditEvent(
                        eventId = item.getString("eventId"),
                        siteId = item.getString("siteId"),
                        action = item.getString("action"),
                        outcome = item.getString("outcome"),
                        detail = item.optString("detail"),
                        timestamp = item.optLong("timestamp")
                    )
                }.getOrNull() ?: continue

                events.add(event)
            }

            events
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeEvents(events: List<WebsiteAuditEvent>) {
        val array = JSONArray()

        events.forEach { event ->
            array.put(
                JSONObject().apply {
                    put("eventId", event.eventId)
                    put("siteId", event.siteId)
                    put("action", event.action)
                    put("outcome", event.outcome)
                    put("detail", event.detail)
                    put("timestamp", event.timestamp)
                }
            )
        }

        check(
            preferences.edit()
                .putString(KEY_EVENTS, array.toString())
                .commit()
        ) {
            "Could not save website access audit history."
        }
    }

    companion object {
        private const val PREFERENCES_NAME =
            "agent_website_access_audit"

        private const val KEY_EVENTS =
            "website_access_events"

        private const val MAX_EVENTS = 500
        private const val MAX_LABEL_LENGTH = 80
        private const val MAX_DETAIL_LENGTH = 500
    }
}
