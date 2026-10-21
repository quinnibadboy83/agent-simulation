
package com.agentsimulation.engine

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/**
 * Local persistent storage for the Android engine shell.
 *
 * Data is stored inside the application's private SharedPreferences.
 * It is not uploaded to a server by this class.
 */
class AgentMemoryStore(context: Context) {

    private val preferences = context.getSharedPreferences(
        PREFERENCES_NAME,
        Context.MODE_PRIVATE
    )

    @Synchronized
    fun loadMessages(): List<ChatMessage> {
        val result = mutableListOf<ChatMessage>()

        return try {
            val json = preferences.getString(KEY_MESSAGES, "[]") ?: "[]"
            val array = JSONArray(json)

            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue

                result.add(
                    ChatMessage(
                        id = item.optString("id", UUID.randomUUID().toString()),
                        role = item.optString("role", "system"),
                        content = item.optString("content", ""),
                        createdAt = item.optLong(
                            "createdAt",
                            System.currentTimeMillis()
                        )
                    )
                )
            }

            result
        } catch (_: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun appendMessage(message: ChatMessage) {
        val messages = loadMessages().toMutableList()
        messages.add(message)

        // Keep the newest 300 messages so the history cannot grow forever.
        val retained = messages.takeLast(MAX_MESSAGES)
        val array = JSONArray()

        retained.forEach { item ->
            array.put(
                JSONObject()
                    .put("id", item.id)
                    .put("role", item.role)
                    .put("content", item.content)
                    .put("createdAt", item.createdAt)
            )
        }

        preferences.edit()
            .putString(KEY_MESSAGES, array.toString())
            .commit()
    }

    @Synchronized
    fun loadApprovals(): List<ApprovalRequest> {
        return try {
            val json = preferences.getString(KEY_APPROVALS, "[]") ?: "[]"
            val array = JSONArray(json)
            val result = mutableListOf<ApprovalRequest>()

            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue

                result.add(
                    ApprovalRequest(
                        id = item.optString(
                            "id",
                            UUID.randomUUID().toString()
                        ),
                        description = item.optString("description", ""),
                        status = item.optString(
                            "status",
                            ApprovalRequest.STATUS_PENDING
                        ),
                        createdAt = item.optLong(
                            "createdAt",
                            System.currentTimeMillis()
                        ),
                        updatedAt = item.optLong(
                            "updatedAt",
                            System.currentTimeMillis()
                        )
                    )
                )
            }

            result.sortedByDescending { it.createdAt }
        } catch (_: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun createApproval(description: String): ApprovalRequest {
        val request = ApprovalRequest(
            description = description.trim()
        )

        val approvals = loadApprovals().toMutableList()
        approvals.add(request)

        saveApprovals(approvals.takeLast(MAX_APPROVALS))
        return request
    }

    /**
     * Resolves only an existing pending request.
     * The returned record represents a decision, not an executed action.
     */
    @Synchronized
    fun resolveApproval(
        requestId: String,
        approved: Boolean
    ): ApprovalRequest? {
        val approvals = loadApprovals().toMutableList()
        val index = approvals.indexOfFirst { it.id == requestId }

        if (index < 0) return null

        val existing = approvals[index]

        // Prevent changing a decision or reusing an approval.
        if (existing.status != ApprovalRequest.STATUS_PENDING) {
            return null
        }

        val updated = existing.copy(
            status = if (approved) {
                ApprovalRequest.STATUS_APPROVED
            } else {
                ApprovalRequest.STATUS_DENIED
            },
            updatedAt = System.currentTimeMillis()
        )

        approvals[index] = updated
        saveApprovals(approvals)
        return updated
    }

    @Synchronized
    fun pendingApprovalCount(): Int {
        return loadApprovals().count {
            it.status == ApprovalRequest.STATUS_PENDING
        }
    }

    private fun saveApprovals(approvals: List<ApprovalRequest>) {
        val array = JSONArray()

        approvals.takeLast(MAX_APPROVALS).forEach { item ->
            array.put(
                JSONObject()
                    .put("id", item.id)
                    .put("description", item.description)
                    .put("status", item.status)
                    .put("createdAt", item.createdAt)
                    .put("updatedAt", item.updatedAt)
            )
        }

        preferences.edit()
            .putString(KEY_APPROVALS, array.toString())
            .commit()
    }

    companion object {
        private const val PREFERENCES_NAME = "agent_simulation_engine_memory"
        private const val KEY_MESSAGES = "conversation_messages"
        private const val KEY_APPROVALS = "creator_approval_requests"
        private const val MAX_MESSAGES = 300
        private const val MAX_APPROVALS = 100
    }
}
