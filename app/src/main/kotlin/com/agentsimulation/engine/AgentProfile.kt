
package com.agentsimulation.engine

/**
 * Describes an agent's identity and assigned responsibilities.
 *
 * This is a role definition, not proof that the agent's AI is running.
 */
data class AgentProfile(
    val id: String,
    val name: String,
    val role: String,
    val description: String,
    val responsibilities: List<String>,
    val enabled: Boolean = true
)
