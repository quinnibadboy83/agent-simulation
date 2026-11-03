
package com.agentsimulation.engine

/**
 * Shared data models for controlled website access.
 *
 * These models describe permissions and stored website configuration.
 * They do not perform browser actions.
 */

enum class WebsiteAccessMethod {
    PUBLIC_WEB,
    OFFICIAL_API,
    AUTHORIZED_BROWSER
}

enum class WebsiteAction {
    READ_PUBLIC,
    READ_ACCOUNT,
    CREATE_DRAFT,
    PUBLISH,
    SEND_MESSAGE,
    PURCHASE,
    MODIFY_ACCOUNT
}

data class WebsiteProfile(
    val siteId: String,
    val displayName: String,
    val baseUrl: String,
    val accessMethod: WebsiteAccessMethod,
    val allowedDomains: List<String>,
    val allowedActions: Set<WebsiteAction>,
    val enabled: Boolean,
    val createdAt: Long,
    val updatedAt: Long
)

data class WebsiteCredentials(
    val loginIdentifier: String = "",
    val password: String = "",
    val apiToken: String = "",
    val extraFields: Map<String, String> = emptyMap()
) {
    fun isEmpty(): Boolean =
        loginIdentifier.isBlank() &&
        password.isBlank() &&
        apiToken.isBlank() &&
        extraFields.values.all { it.isBlank() }
}

/**
 * A short-lived permission grant.
 *
 * Grants are currently in-memory data objects. A future owner-facing
 * approval screen must be the only component allowed to issue grants
 * for sensitive actions.
 */
data class WebsiteAccessGrant(
    val siteId: String,
    val permittedActions: Set<WebsiteAction>,
    val ownerApprovedActions: Set<WebsiteAction>,
    val issuedAt: Long,
    val expiresAt: Long
)

data class WebsiteAccessDecision(
    val allowed: Boolean,
    val requiresOwnerApproval: Boolean,
    val reason: String
)

data class WebsiteAuditEvent(
    val eventId: String,
    val siteId: String,
    val action: String,
    val outcome: String,
    val detail: String,
    val timestamp: Long
)
