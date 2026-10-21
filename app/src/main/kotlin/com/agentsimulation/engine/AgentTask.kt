
package com.agentsimulation.engine

import java.util.UUID

/**
 * Persistent record of work assigned to an agent.
 *
 * A task record tracks intent and status. It does not itself execute work.
 */
data class AgentTask(
    val id: String = UUID.randomUUID().toString(),
    val title: String,
    val instructions: String,
    val assignedAgentId: String,
    val status: String = STATUS_QUEUED,
    val result: String = "",
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
) {
    companion object {
        const val STATUS_QUEUED = "QUEUED"
        const val STATUS_RUNNING = "RUNNING"
        const val STATUS_WAITING_APPROVAL = "WAITING_APPROVAL"
        const val STATUS_COMPLETED = "COMPLETED"
        const val STATUS_FAILED = "FAILED"
        const val STATUS_CANCELLED = "CANCELLED"

        val ALL_STATUSES = setOf(
            STATUS_QUEUED,
            STATUS_RUNNING,
            STATUS_WAITING_APPROVAL,
            STATUS_COMPLETED,
            STATUS_FAILED,
            STATUS_CANCELLED
        )
    }
}
