
package com.agentsimulation.engine

import java.util.UUID

/**
 * A conversation entry saved by the local Agent Simulation Engine.
 */
data class ChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: String,
    val content: String,
    val createdAt: Long = System.currentTimeMillis()
)

/**
 * A proposed consequential action.
 *
 * Approval records a decision only. It does not execute an external action.
 */
data class ApprovalRequest(
    val id: String = UUID.randomUUID().toString(),
    val description: String,
    val status: String = STATUS_PENDING,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
) {
    companion object {
        const val STATUS_PENDING = "PENDING"
        const val STATUS_APPROVED = "APPROVED"
        const val STATUS_DENIED = "DENIED"
    }
}
