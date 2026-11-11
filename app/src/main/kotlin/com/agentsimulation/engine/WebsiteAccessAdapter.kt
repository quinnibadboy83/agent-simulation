
package com.agentsimulation.engine

import java.text.DateFormat
import java.util.Date

/**
 * Lightweight website list presentation helper.
 * Uses existing Android UI components; no RecyclerView dependency.
 */
object WebsiteAccessAdapter {

    fun describe(
        profile: WebsiteProfile,
        hasCredentials: Boolean
    ): String {
        val actions = profile.allowedActions
            .sortedBy { it.name }
            .joinToString(", ") { it.name }

        return buildString {
            appendLine(profile.displayName)
            appendLine(profile.baseUrl)
            appendLine("Access: ${profile.accessMethod.name}")
            appendLine("Status: ${if (profile.enabled) "Enabled" else "Disabled"}")
            appendLine("Credentials: ${if (hasCredentials) "Saved securely" else "Not configured"}")
            appendLine("Permitted actions: $actions")
            append("Updated: ${DateFormat.getDateTimeInstance().format(Date(profile.updatedAt))}")
        }
    }

    fun actionLabel(action: WebsiteAction): String {
        return when (action) {
            WebsiteAction.READ_PUBLIC -> "Read public pages"
            WebsiteAction.READ_ACCOUNT -> "Read account information"
            WebsiteAction.CREATE_DRAFT -> "Create drafts"
            WebsiteAction.PUBLISH -> "Publish content"
            WebsiteAction.SEND_MESSAGE -> "Send messages"
            WebsiteAction.PURCHASE -> "Make purchases"
            WebsiteAction.MODIFY_ACCOUNT -> "Modify account settings"
        }
    }
}
