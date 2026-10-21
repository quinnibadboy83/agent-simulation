
package com.agentsimulation.engine

/**
 * Initial roster for the Agent Simulation Engine.
 *
 * These are role definitions only. They do not imply that model inference,
 * financial authority, or external tools are currently connected.
 */
object AgentRoster {

    val defaultAgents: List<AgentProfile> = listOf(
        AgentProfile(
            id = "boss",
            name = "Boss",
            role = "Super Overseer",
            description = "Coordinates work and reports the overall situation.",
            responsibilities = listOf(
                "Receive creator instructions",
                "Break goals into tasks",
                "Coordinate specialist agents",
                "Report task progress and results"
            )
        ),
        AgentProfile(
            id = "banker",
            name = "Banker",
            role = "Financial Authority",
            description = "Tracks the simulation economy and financial proposals.",
            responsibilities = listOf(
                "Track simulated balances",
                "Review proposed costs and revenue",
                "Report financial outcomes"
            )
        ),
        AgentProfile(
            id = "info-farmer",
            name = "Info Farmer",
            role = "Research Specialist",
            description = "Collects and organises research for review.",
            responsibilities = listOf(
                "Research public information",
                "Summarise findings",
                "Record useful sources"
            )
        ),
        AgentProfile(
            id = "opportunity",
            name = "Opportunity Agent",
            role = "Opportunity Research",
            description = "Evaluates potential projects and revenue opportunities.",
            responsibilities = listOf(
                "Identify potential opportunities",
                "Compare risks and requirements",
                "Prepare proposals for creator review"
            )
        )
    )

    fun find(agentId: String): AgentProfile? {
        return defaultAgents.firstOrNull { it.id == agentId }
    }
}
