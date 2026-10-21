
package com.agentsimulation.engine

/**
 * Creator-controlled approval gate for proposed consequential actions.
 *
 * This class records approval decisions only. It deliberately does not
 * execute network requests, purchases, messages, account changes, or posts.
 */
class CreatorApprovalGate(
    private val memoryStore: AgentMemoryStore
) {

    fun requestApproval(description: String): ApprovalRequest? {
        val cleaned = description.trim()

        if (cleaned.isBlank()) return null
        if (cleaned.length > MAX_DESCRIPTION_LENGTH) return null

        return memoryStore.createApproval(cleaned)
    }

    fun approve(requestId: String): ApprovalRequest? {
        return memoryStore.resolveApproval(
            requestId = requestId,
            approved = true
        )
    }

    fun deny(requestId: String): ApprovalRequest? {
        return memoryStore.resolveApproval(
            requestId = requestId,
            approved = false
        )
    }

    companion object {
        private const val MAX_DESCRIPTION_LENGTH = 2000
    }
}
