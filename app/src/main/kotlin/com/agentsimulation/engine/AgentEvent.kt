
package com.agentsimulation.engine

import java.util.UUID

/**
 * Describes an operational event that the station UI can observe.
 *
 * Events report recorded state changes; they do not grant permissions.
 */
data class AgentEvent(
    val id: String = UUID.randomUUID().toString(),
    val type: String,
    val message: String,
    val agentId: String? = null,
    val taskId: String? = null,
    val createdAt: Long = System.currentTimeMillis()
) {
    companion object {
        const val AGENT_REGISTERED = "AGENT_REGISTERED"
        const val TASK_CREATED = "TASK_CREATED"
        const val TASK_STATUS_CHANGED = "TASK_STATUS_CHANGED"
        const val TASK_RESULT_RECORDED = "TASK_RESULT_RECORDED"
        const val SYSTEM_NOTICE = "SYSTEM_NOTICE"
    }
}
