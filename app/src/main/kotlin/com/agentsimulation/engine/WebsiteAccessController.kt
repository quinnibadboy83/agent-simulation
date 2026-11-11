
package com.agentsimulation.engine

import android.content.Context

/**
 * Coordinates website registration, permissions, credentials and audit.
 *
 * This class does not perform browser or network actions.
 */
class WebsiteAccessController(context: Context) {

    val registry = WebsiteAccessRegistry(context.applicationContext)
    val policy = WebsitePermissionPolicy()
    val auditLog = WebsiteAccessAuditLog(context.applicationContext)
    val credentialVault = WebsiteCredentialVault(
        context.applicationContext,
        registry
    )

    fun registerWebsite(
        displayName: String,
        baseUrl: String,
        accessMethod: WebsiteAccessMethod,
        allowedActions: Set<WebsiteAction>
    ): WebsiteProfile {
        val profile = registry.create(
            displayName = displayName,
            baseUrl = baseUrl,
            accessMethod = accessMethod,
            allowedActions = allowedActions,
            enabled = true
        )

        auditLog.record(
            siteId = profile.siteId,
            action = "REGISTER_WEBSITE",
            outcome = "SUCCESS",
            detail = "Website profile registered."
        )

        return profile
    }

    fun setWebsiteEnabled(
        siteId: String,
        enabled: Boolean
    ): Boolean {
        val changed = registry.setEnabled(siteId, enabled)

        auditLog.record(
            siteId = siteId,
            action = if (enabled) "ENABLE_WEBSITE" else "DISABLE_WEBSITE",
            outcome = if (changed) "SUCCESS" else "FAILED",
            detail = "Website enabled state changed."
        )

        return changed
    }

    fun deleteWebsite(siteId: String): Boolean {
        val removed = registry.delete(siteId)

        if (removed) {
            credentialVault.delete(siteId)
        }

        auditLog.record(
            siteId = siteId,
            action = "DELETE_WEBSITE",
            outcome = if (removed) "SUCCESS" else "FAILED",
            detail = "Website profile deletion requested."
        )

        return removed
    }

    fun evaluateAction(
        siteId: String,
        action: WebsiteAction,
        grant: WebsiteAccessGrant?
    ): WebsiteAccessDecision {
        val profile = registry.get(siteId)

        if (profile == null) {
            val decision = WebsiteAccessDecision(
                allowed = false,
                requiresOwnerApproval = false,
                reason = "Website is not registered."
            )

            auditLog.record(
                siteId = siteId,
                action = action.name,
                outcome = "DENIED",
                detail = decision.reason
            )

            return decision
        }

        val decision = policy.evaluate(
            profile = profile,
            action = action,
            grant = grant
        )

        auditLog.record(
            siteId = siteId,
            action = action.name,
            outcome = if (decision.allowed) "ALLOWED" else "DENIED",
            detail = decision.reason
        )

        return decision
    }

    fun isUrlAllowed(
        siteId: String,
        url: String
    ): Boolean {
        val profile = registry.get(siteId) ?: return false
        return policy.isUrlAllowed(profile, url)
    }

    fun recordCredentialSave(siteId: String) {
        auditLog.record(
            siteId = siteId,
            action = "SAVE_CREDENTIALS",
            outcome = "SUCCESS",
            detail = "Encrypted credential record saved."
        )
    }

    fun recordCredentialDelete(siteId: String) {
        auditLog.record(
            siteId = siteId,
            action = "DELETE_CREDENTIALS",
            outcome = "SUCCESS",
            detail = "Credential record deletion requested."
        )
    }
}
